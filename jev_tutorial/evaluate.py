"""Run the small teaching dataset. Save measurements, including failures."""

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from .classifier import MODEL, ROOT, classify_ticket, make_client


def summarize(rows):
    successful = [r for r in rows if "result" in r]
    automated = [r for r in successful if not r["result"]["policy"]["review_required"]]
    durations = sorted(r["result"]["elapsed_ms"] for r in successful)
    input_tokens = sum(r["result"]["usage"]["input_tokens"] for r in successful)
    return {
        "attempted": len(rows),
        "successful": len(successful),
        "api_failures": len(rows) - len(successful),
        "correct_team": sum(r["team_correct"] for r in successful),
        "team_accuracy_on_successful": (sum(r["team_correct"] for r in successful) / len(successful)
                                        if successful else None),
        "automatic_routes": len(automated),
        "automation_coverage": len(automated) / len(rows) if rows else 0,
        "wrong_automatic_team_routes": sum(not r["team_correct"] for r in automated),
        "automatic_team_error_rate": (sum(not r["team_correct"] for r in automated) / len(automated)
                                      if automated else None),
        "median_ms": statistics.median(durations) if durations else None,
        "p95_ms": durations[math.ceil(len(durations) * .95) - 1] if durations else None,
        "input_tokens": input_tokens,
        "estimated_successful_input_cost_usd": round(input_tokens * .042 / 1_000_000, 8),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "local-data/evaluation.json")
    args = parser.parse_args()
    cases = json.loads((ROOT / "data/tickets.json").read_text())
    rows = []
    with make_client() as client:
        for case in cases:
            row = {"id": case["id"], "expected_team": case["expected_team"],
                   "expected_refund": case["expected_refund"]}
            try:
                result = classify_ticket({"subject": case["subject"], "body": case["body"]}, client)
                row.update(result=result, team_correct=result["answers"]["team"]["choice"] == case["expected_team"])
                print(case["id"], result["answers"]["team"]["choice"],
                      "match" if row["team_correct"] else "MISMATCH",
                      result["elapsed_ms"], "ms")
            except Exception as error:
                row["error_type"] = type(error).__name__
                print(case["id"], "API FAILURE", row["error_type"])
            rows.append(row)
    report = {
        "model": MODEL,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "method": "12 synthetic teaching cases, sequential, reused client, no warm-up, no retries. Not a held-out benchmark.",
        "pricing": "Direct API input price $0.042/M, checked 2026-09-21. Output free. Failed-call usage unknown.",
        "summary": summarize(rows),
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    print("Saved:", args.output)
    return 1 if report["summary"]["api_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
