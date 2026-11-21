#!/usr/bin/env python3
"""findings_verifier.py — check a second model's review findings against the real files.

A reviewing model can cite a file that does not exist, a line past the end of the
file, or code that is not there. This verifier checks each finding's location (and
an optional verbatim `evidence` quote) against the working tree, orders the survivors
by severity, and refuses to let a rejected finding be presented as a finding.

Input follows the common review shape: {verdict, summary, findings[{severity, title,
body, file, line_start, line_end, confidence, recommendation, evidence?}], next_steps}.

Per finding: VERIFIED (location ok and evidence quote found), LOCATED (location ok,
no quote to check), REJECTED (bad path, out-of-range lines, or quote not in range).
A reviewer's verdict that contradicts its findings is also a rejection.

Standard library only.

Exit codes:
    0  no finding rejected
    2  usage error
    3  input is not valid findings JSON
    4  at least one finding or the verdict was rejected
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3}
REQUIRED = ("severity", "title", "body", "file", "line_start", "line_end")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def check(f: dict, repo: str) -> tuple[str, list[str]]:
    why: list[str] = []
    missing = [k for k in REQUIRED if k not in f]
    if missing:
        return "REJECTED", [f"missing fields: {', '.join(missing)}"]
    if f["severity"] not in SEV:
        why.append(f"unknown severity '{f['severity']}'")
    conf = f.get("confidence")
    if conf is not None and not (isinstance(conf, (int, float)) and 0 <= conf <= 1):
        why.append("confidence outside 0..1")
    path = os.path.realpath(os.path.join(repo, f["file"]))
    root = os.path.realpath(repo)
    if not path.startswith(root + os.sep):
        return "REJECTED", ["path escapes the repo"]
    if not os.path.isfile(path):
        return "REJECTED", [f"file not found: {f['file']}"]
    try:
        ls, le = int(f["line_start"]), int(f["line_end"])
    except (TypeError, ValueError):
        return "REJECTED", ["line numbers are not integers"]
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if ls < 1 or le < ls:
        why.append(f"bad line range {ls}-{le}")
    elif le > len(lines):
        why.append(f"line {le} is past end of file ({len(lines)} lines)")
    if why:
        return "REJECTED", why
    quote = f.get("evidence")
    if not quote:
        return "LOCATED", ["no evidence quote — location checked, claim not mechanically verifiable"]
    window = norm(" ".join(lines[max(0, ls - 1 - 2): le + 2]))  # allow 2 lines of drift
    if norm(quote) in window:
        return "VERIFIED", []
    return "REJECTED", ["evidence quote not found near the cited lines (stale or fabricated)"]


def run(data: dict, repo: str) -> dict:
    out, problems = [], []
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise ValueError("'findings' must be a list")
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            raise ValueError(f"findings[{i}] is not an object")
        status, why = check(f, repo)
        out.append({"index": i, "status": status, "notes": why, "finding": f})
    verdict = data.get("verdict")
    bad_sev = [o for o in out if o["finding"].get("severity") in ("critical", "high")
               and o["status"] != "REJECTED"]
    if verdict == "approve" and bad_sev:
        problems.append("verdict is 'approve' but critical/high findings stand")
    if verdict == "needs-attention" and not findings:
        problems.append("verdict is 'needs-attention' with no findings")
    out.sort(key=lambda o: (o["status"] == "REJECTED", SEV.get(o["finding"].get("severity"), 9),
                            -float(o["finding"].get("confidence") or 0)))
    rejected = [o for o in out if o["status"] == "REJECTED"]
    return {"verdict": verdict, "summary": data.get("summary", ""), "results": out,
            "present": [o for o in out if o["status"] != "REJECTED"],
            "rejected_count": len(rejected), "verdict_problems": problems,
            "next_step": "Present findings in this order, then STOP and ask the user which, "
                         "if any, to fix. Do not edit files."}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("findings", nargs="?", help="findings JSON file")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--output", choices=["text", "json"], default="text")
    a = ap.parse_args()
    try:
        if a.sample:
            here = os.path.dirname(os.path.abspath(__file__))
            a.findings = os.path.join(here, "..", "assets", "findings.example.json")
            a.repo = os.path.join(here)
        if not a.findings:
            ap.error("pass a findings JSON file or --sample")
        with open(a.findings, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("top level must be an object")
        res = run(data, a.repo)
    except (OSError, ValueError) as e:
        print(f"invalid input: {e}", file=sys.stderr)
        return 3
    if a.output == "json":
        print(json.dumps(res, indent=2))
    else:
        print(f"reviewer verdict: {res['verdict']}  — {res['summary']}")
        for o in res["results"]:
            f = o["finding"]
            print(f"[{o['status']:<8}] {str(f.get('severity')):<8} {f.get('file')}:{f.get('line_start')}-{f.get('line_end')}  {f.get('title')}")
            for n in o["notes"]:
                print(f"            · {n}")
        for p in res["verdict_problems"]:
            print(f"VERDICT PROBLEM: {p}")
        print(res["next_step"])
    return 4 if res["rejected_count"] or res["verdict_problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
