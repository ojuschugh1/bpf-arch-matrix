#!/usr/bin/env python3
"""Run every probe case and write a per-environment results JSON; probe exit codes: 0 pass, 1 fail, 2 skip."""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"
STATUS = {0: "pass", 1: "fail", 2: "skip"}


def os_pretty():
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.system()


def bpftrace_version():
    exe = shutil.which("bpftrace")
    if not exe:
        return None
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
        return (p.stdout or p.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def discover():
    cases = []
    for meta in sorted(CASES.glob("*/case.json")):
        with open(meta) as f:
            data = json.load(f)
        data["_dir"] = meta.parent
        cases.append(data)
    return cases


def run_case(case, timeout):
    probe = case["_dir"] / "probe.sh"
    if not probe.exists():
        return "error", "probe.sh missing", ""
    try:
        p = subprocess.run(
            ["bash", str(probe)], capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return "error", f"harness timeout after {timeout}s", ""
    output = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    reason = ""
    for line in output.splitlines():
        if line.startswith("reason: "):
            reason = line[len("reason: "):].strip()
    status = STATUS.get(p.returncode, "error")
    if status == "error" and not reason:
        reason = f"probe exited with unexpected code {p.returncode}"
    evidence = "\n".join(output.splitlines()[-25:])
    return status, reason, evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=None, help="environment label, e.g. ubuntu-24.04-arm")
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--timeout", type=int, default=120, help="per-probe timeout in seconds")
    ap.add_argument("--list", action="store_true", help="list cases without running")
    args = ap.parse_args()

    cases = discover()
    if args.list:
        for c in cases:
            print(f"{c['id']}: {c['title']}")
        return 0

    label = args.label or f"{os_pretty()}-{platform.machine()}"
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", label)

    run_url = None
    if os.environ.get("GITHUB_RUN_ID"):
        run_url = "{}/{}/actions/runs/{}".format(
            os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
            os.environ.get("GITHUB_REPOSITORY", ""),
            os.environ["GITHUB_RUN_ID"],
        )

    results = []
    for c in cases:
        status, reason, evidence = run_case(c, args.timeout)
        results.append(
            {
                "id": c["id"],
                "title": c["title"],
                "category": c.get("category", ""),
                "status": status,
                "reason": reason,
                "evidence": evidence,
            }
        )
        print(f"[{status:>5}] {c['id']}: {reason}")

    doc = {
        "label": label,
        "arch": platform.machine(),
        "kernel": platform.release(),
        "os": os_pretty(),
        "bpftrace": bpftrace_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_url": run_url,
        "provenance": "tested-here",
        "cases": results,
    }

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"results-{label}.json"
    outfile.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"\nwrote {outfile}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### {label} ({platform.machine()}, kernel {platform.release()})\n\n")
            f.write("| case | status | reason |\n|---|---|---|\n")
            for r in results:
                f.write(f"| {r['id']} | {r['status']} | {r['reason']} |\n")
            f.write("\n")

    if results and all(r["status"] == "error" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
