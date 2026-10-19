"""Explicit-input math ledger. Never guesses financial inputs from prose."""
from decimal import Decimal
import argparse
import json
from pathlib import Path


def calculate(operation, values, unit, source_ids):
    if not unit or not source_ids or not values:
        raise ValueError("Every calculation needs units and source ids")
    v = [Decimal(str(n)) for n in values]
    if any(not x.is_finite() for x in v):
        raise ValueError("Nonfinite inputs are not financial data")
    if operation == "sum":
        answer = sum(v)
    elif operation in ("ratio_pct", "growth_pct"):
        if len(v) != 2 or v[1] == 0:
            raise ValueError("Ratio requires two values and a nonzero denominator")
        if operation == "growth_pct" and v[1] < 0:
            raise ValueError("Growth from a negative base needs a separate interpretation")
        answer = (v[0] / v[1] - (1 if operation == "growth_pct" else 0)) * 100
    elif operation == "difference":
        if len(v) != 2:
            raise ValueError("Difference requires two comparable inputs")
        answer = v[0] - v[1]
    else:
        raise ValueError("Unknown operation")
    return {"operation": operation, "inputs": [str(x) for x in v], "input_unit": unit, "result": str(answer), "source_ids": source_ids, "interpretation": "code_computed; input accuracy and comparability must be verified separately"}


def ledger(entries):
    result = []
    for entry in entries:
        row = calculate(entry["operation"], entry["values"], entry["unit"], entry["source_ids"])
        row.update(id=entry["id"], claim_id=entry["claim_id"], scope=entry["scope"])
        row["matches_stated_value"] = abs(Decimal(row["result"]) - Decimal(str(entry["stated_value"]))) <= Decimal(str(entry["tolerance"]))
        result.append(row)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = ledger(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Explicit calculations checked: {sum(r['matches_stated_value'] for r in result)}/{len(result)}")
