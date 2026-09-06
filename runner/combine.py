#!/usr/bin/env python3
"""Merge per-environment results JSONs into one matrix (markdown + JSON)."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def main():
    docs = []
    for f in sorted(RESULTS.glob("results-*.json")):
        with open(f) as fh:
            docs.append(json.load(fh))
    if not docs:
        print("no results found in results/", file=sys.stderr)
        return 1

    labels = [d["label"] for d in docs]
    case_ids = []
    case_titles = {}
    for d in docs:
        for c in d["cases"]:
            if c["id"] not in case_ids:
                case_ids.append(c["id"])
                case_titles[c["id"]] = c["title"]

    cell = {(d["label"], c["id"]): c for d in docs for c in d["cases"]}

    lines = ["# bpf-arch-matrix results", ""]
    for d in docs:
        line = f"- **{d['label']}**: {d['os']}, kernel {d['kernel']}, {d['arch']}"
        if d.get("run_url"):
            line += f", [run]({d['run_url']})"
        lines.append(line)
    lines += [
        "",
        "| case | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for cid in case_ids:
        row = [cid]
        for lab in labels:
            c = cell.get((lab, cid))
            row.append(c["status"] if c else "n/a")
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "Every cell above was produced by this repository's CI (provenance: tested-here).",
        "Reasons and evidence are in the per-environment JSON artifacts.",
        "",
    ]
    md = "\n".join(lines)

    (ROOT / "matrix.md").write_text(md)
    (ROOT / "matrix.json").write_text(
        json.dumps(
            {
                "environments": [
                    {
                        k: d.get(k)
                        for k in ("label", "os", "kernel", "arch", "bpftrace", "timestamp", "run_url")
                    }
                    for d in docs
                ],
                "cases": [
                    {
                        "id": cid,
                        "title": case_titles[cid],
                        "results": {
                            lab: cell.get((lab, cid), {}).get("status", "n/a") for lab in labels
                        },
                    }
                    for cid in case_ids
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(md)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(md + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
