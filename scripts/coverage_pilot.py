"""Run the three-way MedlinePlus coverage pilot over a CSV of terms.

Input CSV columns:
    term

Output CSV columns:
    term, category, title, url, causal_risk, diagnostic_risk, prognostic_risk, treatment_risk

This script intentionally leaves adjudication as a human-reviewed step.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import re
from pathlib import Path

from app.retrieval.medlineplus import MedlinePlusRetriever


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    args = parser.parse_args()

    retriever = MedlinePlusRetriever()
    rows = []
    with open(args.input_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row["term"].strip())

    output = []
    for term in rows:
        hits = await retriever.web_search(term, top_k=3)
        if not hits:
            output.append({"term": term, "category": "NO_HIT"})
            continue
        first = hits[0]
        merged = " ".join(h.text for h in hits).lower()
        # These are risk flags for adjudication, not automatic safety decisions.
        risk = {
            "causal_risk": bool(re.search(r"cause|caused|due to|associated with", merged)),
            "diagnostic_risk": bool(re.search(r"diagnos|disease|condition", merged)),
            "prognostic_risk": bool(re.search(r"prognos|outlook|survival", merged)),
            "treatment_risk": bool(re.search(r"treat|medication|surgery|therapy", merged)),
        }
        output.append({
            "term": term,
            "category": "HIT_REQUIRES_HUMAN_ADJUDICATION",
            "title": first.title,
            "url": first.url or "",
            **risk,
        })

    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = sorted({k for r in output for k in r.keys()})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    asyncio.run(main())
