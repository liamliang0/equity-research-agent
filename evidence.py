"""Deterministic evidence artifacts and review gates, independent of LLM narration."""
import csv
import hashlib
import json
from datetime import date
from pathlib import Path


def artifacts(report, assets, output):
    output = Path(output)
    sources = {s["id"]: s for s in report["sources"]}
    checks = {s["id"]: s for s in report["audit"]["sources"]}
    assets = {a["id"]: a for a in assets}
    facts = {f["id"]: f for f in report["facts"]}
    rows, flags = [], []
    for f in facts.values():
        for sid in f["source_ids"]:
            s = sources[sid]
            age = (date.fromisoformat(report["as_of"]) - date.fromisoformat(s["published"])).days if s["published"] else None
            rows.append({"asset": f["company"], "fact_id": f["id"], "claim": f["claim"], "claim_type": f.get("claim_type", "model_extracted_claim"), "source_id": sid, "source_url": s["url"], "published": s["published"], "source_status": checks[sid]["status"], "age_days": age})
            if age is not None and age > 120:
                flags.append(f"{f['id']}: 来源距研究截止日超过120天，需检查有无更新披露。")
        if any(token in f["claim"] for token in ("据此计算", "合计", "加总", "相差")):
            flags.append(f"{f['id']}: 出现派生计算；除非 calculation-ledger.json 有对应输入与公式，否则不得当作代码复算结果。")
        if f["audit"] != "source_excerpt_matched":
            flags.append(f"{f['id']}: 来源未全部匹配，需要复核。")
    with (output / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["asset", "fact_id"])
        writer.writeheader()
        writer.writerows(rows)
    ledger = []
    for c in report["companies"]:
        ledger.append({"asset": c["id"], "instrument_kind": assets[c["id"]]["kind"], "as_of": report["as_of"], "current_thesis": c["summary"], "support": c["support"], "counterpoints": c["counterpoints"], "invalidation": c["invalidation"], "next_checks": c["next_checks"], "unknowns": c["unknowns"], "source_review_required": any(f["company"] == c["id"] and f["audit"] != "source_excerpt_matched" for f in facts.values())})
    (output / "thesis-ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    review = ["# 程序审查记录", "", "本记录是规则检查，不是独立模型的事实审计，也不证明投资结论正确。", "", f"- 证券覆盖：{len(assets)}；事实引用关系保留在 evidence.csv。", f"- 原文片段匹配：{report['audit']['matched']}/{report['audit']['total']}。", "- 反方观点与研究观点来自同一次模型调用，不冒充多个独立分析师。", "- 未知事项和失效条件保留，不以中性结论掩盖运行失败。", "", "## 需关注项", ""]
    review += ["- " + f for f in sorted(set(flags))] or ["- 未触发上述规则；仍需人工检查关键数字和推理。"]
    (output / "review.md").write_text("\n".join(review) + "\n", encoding="utf-8")
    return {"review_flags": sorted(set(flags)), "evidence_rows": len(rows), "thesis_objects": len(ledger)}


def manifest(folder, filenames):
    folder = Path(folder)
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in filenames if (folder / name).is_file()}
