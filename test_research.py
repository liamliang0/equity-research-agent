import copy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import calculations
import evidence
import research_agent as r


def fixture():
    sources = [{"id": "apple", "title": "Issuer statement", "url": "https://www.apple.com/newsroom/test/", "published": "2026-09-01", "verification_excerpt": "Revenue and cash flow data are included in this release"}, {"id": "fund", "title": "Fund facts", "url": "https://www.ssga.com/test/", "published": None, "verification_excerpt": "The fund seeks to track the performance of the index"}]
    facts = [{"id": f"{a}-{i}", "company": a, "claim": "Synthetic test claim, not market data", "source_ids": ["apple" if a == "AAPL" else "fund"]} for a in ("AAPL", "SPY") for i in range(2)]
    companies = []
    for a in ("AAPL", "SPY"):
        point = {"text": "Synthetic conditional interpretation", "fact_ids": [f"{a}-0"]}
        companies.append({"id": a, "summary": point, "support": [point], "counterpoints": [point], "invalidation": ["future evidence would reverse view"], "next_checks": ["next disclosure"], "unknowns": ["not known"]})
    return {"as_of": "2026-10-19", "question": "Synthetic test", "sources": sources, "facts": facts, "companies": companies, "comparison": [], "changes_from_baseline": [], "scope_limitations": ["fixture only"]}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.assets = r.load_watchlist(r.SOURCE_ROOT / "watchlist.example.json")
        self.temp = tempfile.TemporaryDirectory(dir=r.SOURCE_ROOT)
        r.configure(self.assets, self.temp.name)
        self.report = fixture()

    def tearDown(self):
        self.temp.cleanup()

    def test_equity_and_etf_are_distinct(self):
        self.assertEqual({a["kind"] for a in self.assets}, {"equity", "etf"})
        self.assertIn("etf", r.prompt_for("test", {}, "2026-10-19"))

    def test_no_three_ticker_hardcode(self):
        r.configure([self.assets[0]], self.temp.name)
        self.assertEqual(r.COMPANIES, {"AAPL"})
        self.assertNotIn("SKHYNIX", json.dumps(r.SCHEMA))

    def test_watchlist_duplicate_is_rejected(self):
        p = Path(self.temp.name) / "bad.json"
        p.write_text(json.dumps({"assets": [self.assets[0], self.assets[0]]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            r.load_watchlist(p)

    def test_extra_broker_fields_are_not_sent_to_model(self):
        raw = copy.deepcopy(self.assets)
        raw[0].update(position=123, average_price=999, unrealized_pnl=456)
        p = Path(self.temp.name) / "broker.json"
        p.write_text(json.dumps({"assets": raw}), encoding="utf-8")
        cleaned = r.load_watchlist(p)
        self.assertNotIn("position", cleaned[0])
        self.assertNotIn("average_price", cleaned[0])
        self.assertNotIn("unrealized_pnl", cleaned[0])

    def test_local_source_url_is_rejected(self):
        self.report["sources"][0]["url"] = "https://127.0.0.1/private"
        with self.assertRaises(ValueError):
            r.validate_report(self.report, "2026-10-19")

    def test_other_issuer_not_registered_is_rejected(self):
        self.report["sources"][0]["url"] = "https://unregistered.example/report"
        with self.assertRaises(ValueError):
            r.validate_report(self.report, "2026-10-19")

    def test_future_source_is_rejected(self):
        self.report["sources"][0]["published"] = "2026-10-20"
        with self.assertRaises(ValueError):
            r.validate_report(self.report, "2026-10-19")

    def test_missing_instrument_rejected(self):
        self.report["companies"].pop()
        with self.assertRaises(ValueError):
            r.validate_report(self.report, "2026-10-19")

    def test_invented_fact_reference_rejected(self):
        self.report["companies"][0]["summary"]["fact_ids"] = ["invented"]
        with self.assertRaises(ValueError):
            r.validate_report(self.report, "2026-10-19")

    def test_company_evidence_not_interchangeable(self):
        self.report["companies"][0]["summary"]["fact_ids"] = ["SPY-0"]
        with self.assertRaises(ValueError):
            r.validate_report(self.report, "2026-10-19")

    def test_both_assets_have_two_facts(self):
        r.validate_report(self.report, "2026-10-19")

    def test_failed_source_is_visible(self):
        with patch.object(r, "verify_source", side_effect=lambda s: {"id": s["id"], "status": "fetch_failed" if s["id"] == "fund" else "excerpt_matched"}):
            self.report["audit"] = r.audit(self.report)
        text = r.markdown(self.report, self.report["audit"], "fixture")
        self.assertIn("来源待复核", text)
        self.assertEqual(self.report["audit"]["matched"], 1)

    def test_evidence_and_thesis_artifacts(self):
        with patch.object(r, "verify_source", side_effect=lambda s: {"id": s["id"], "status": "excerpt_matched"}):
            self.report["audit"] = r.audit(self.report)
        summary = evidence.artifacts(self.report, self.assets, Path(self.temp.name))
        self.assertEqual(summary["evidence_rows"], 4)
        self.assertEqual(summary["thesis_objects"], 2)
        ledger = json.loads((Path(self.temp.name) / "thesis-ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger[1]["instrument_kind"], "etf")

    def test_manifest_changes_if_artifact_changes(self):
        p = Path(self.temp.name) / "report.md"
        p.write_text("first", encoding="utf-8")
        before = evidence.manifest(self.temp.name, ["report.md"])
        p.write_text("second", encoding="utf-8")
        self.assertNotEqual(before, evidence.manifest(self.temp.name, ["report.md"]))

    def test_model_html_is_escaped(self):
        self.assertNotIn("<script>", r.render_html("<script>alert(1)</script>"))

    def test_excerpt_normalization(self):
        self.assertEqual(r.norm("Cash\n &amp; revenue"), r.norm("cash & revenue"))


class CalculationTests(unittest.TestCase):
    def test_growth_with_sources(self):
        self.assertEqual(calculations.calculate("growth_pct", [120, 100], "USD", ["s"])["result"], "20.0")

    def test_negative_base_not_misleading_growth(self):
        with self.assertRaises(ValueError):
            calculations.calculate("growth_pct", [10, -10], "USD", ["s"])

    def test_zero_denominator_not_zero_growth(self):
        with self.assertRaises(ValueError):
            calculations.calculate("ratio_pct", [1, 0], "USD", ["s"])

    def test_nonfinite_is_not_data(self):
        with self.assertRaises(ValueError):
            calculations.calculate("sum", ["NaN"], "%", ["s"])

    def test_input_sources_required(self):
        with self.assertRaises(ValueError):
            calculations.calculate("sum", [1, 2], "%", [])

    def test_tracking_difference_in_percentage_points(self):
        self.assertEqual(Decimal(calculations.calculate("difference", [15.60, 15.74], "pp", ["s"])["result"]), Decimal("-0.14"))


if __name__ == "__main__":
    unittest.main()
