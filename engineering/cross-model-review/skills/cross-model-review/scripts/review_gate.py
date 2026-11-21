#!/usr/bin/env python3
"""review_gate.py — decide whether a second-model review of a change is worth running.

A second-model review (Codex, Gemini, another Claude) costs wall-clock time and
budget, and an unneeded one trains people to ignore the output. This gate takes the
size and risk of a change and returns one verdict: SKIP, RUN-FOREGROUND,
RUN-BACKGROUND, or RUN-ADVERSARIAL (risk paths touched). It never runs a review.

It refuses rather than guesses:
  * an empty change (exit 3) — nothing to review is a finding, not a verdict;
  * missing inputs (exit 4) — pass --git or --files/--lines.

Standard library only. No network, no model calls.

Exit codes:
    0  verdict produced
    2  usage error
    3  nothing to review
    4  inputs insufficient to decide
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys

RISK_CLASSES = {
    "auth-and-permissions": r"(auth|permission|acl|rbac|oauth|login|session|token|jwt)",
    "money": r"(payment|billing|invoice|stripe|ledger|checkout)",
    "data-migration": r"(migrat|schema|alembic|\.sql$|backfill)",
    "secrets-and-crypto": r"(secret|crypto|cipher|\.pem$|\.env|keystore)",
    "infra-and-ci": r"(terraform|\.github/workflows|dockerfile|helm|k8s|kubernetes|deploy)",
    "concurrency": r"(lock|mutex|queue|worker|retry|idempot|transaction)",
}
DOC_ONLY = re.compile(r"\.(md|rst|txt|adoc)$", re.I)

TINY_FILES, TINY_LINES = 2, 150  # foreground only when clearly small


def classify(paths: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for p in paths:
        for name, pat in RISK_CLASSES.items():
            if re.search(pat, p, re.I):
                hits.setdefault(name, []).append(p)
    return hits


def decide(files: int, lines: int, paths: list[str], tests_changed: bool,
           fingerprint: str | None, reviewed: str | None) -> dict:
    risks = classify(paths)
    reasons: list[str] = []
    if files == 0 and lines == 0:
        return {"verdict": "NOTHING-TO-REVIEW", "reasons": ["empty change"], "risks": {}}
    if reviewed and fingerprint and reviewed == fingerprint:
        return {"verdict": "SKIP", "reasons": ["this exact diff was already reviewed"],
                "risks": risks}
    if paths and all(DOC_ONLY.search(p) for p in paths) and not risks:
        return {"verdict": "SKIP", "reasons": ["docs-only change, no risk paths"], "risks": {}}
    if lines < 10 and not risks:
        return {"verdict": "SKIP", "reasons": [f"{lines} changed lines and no risk path"],
                "risks": {}}
    if risks:
        reasons.append("risk paths touched: " + ", ".join(sorted(risks)))
        verdict = "RUN-ADVERSARIAL"
    elif files <= TINY_FILES and lines <= TINY_LINES:
        reasons.append(f"small change ({files} files, {lines} lines)")
        verdict = "RUN-FOREGROUND"
    else:
        reasons.append(f"larger change ({files} files, {lines} lines)")
        verdict = "RUN-BACKGROUND"
    if not tests_changed and lines >= 40:
        reasons.append("no test files changed — a reviewer will likely ask for them")
    if verdict == "RUN-ADVERSARIAL" and (files > TINY_FILES or lines > TINY_LINES):
        reasons.append("run in the background; adversarial passes are slow")
    return {"verdict": verdict, "reasons": reasons, "risks": risks}


def from_git(repo: str) -> tuple[int, int, list[str], str]:
    def run(*a: str) -> str:
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True,
                              timeout=30).stdout
    names = [n for n in run("diff", "--name-only", "HEAD").splitlines() if n]
    untracked = [n for n in run("ls-files", "--others", "--exclude-standard").splitlines() if n]
    stat = run("diff", "--shortstat", "HEAD")
    m = re.findall(r"(\d+) (?:insertion|deletion)", stat)
    lines = sum(int(x) for x in m)
    # untracked files are reviewable work even when the diff stat is empty
    for u in untracked:
        try:
            with open(f"{repo}/{u}", "rb") as fh:
                lines += sum(1 for _ in fh)
        except OSError:
            pass
    paths = sorted(set(names + untracked))
    fp = hashlib.sha256((run("diff", "HEAD") + "\n".join(untracked)).encode()).hexdigest()[:12]
    return len(paths), lines, paths, fp


SAMPLE = {"files": 4, "lines": 210, "paths": ["src/auth/session.py", "tests/test_session.py",
          "docs/notes.md", "src/api/routes.py"], "tests_changed": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--git", metavar="REPO", help="measure the working tree of this repo")
    ap.add_argument("--files", type=int)
    ap.add_argument("--lines", type=int, help="changed lines (insertions + deletions)")
    ap.add_argument("--paths", help="comma-separated changed paths (enables risk detection)")
    ap.add_argument("--tests-changed", action="store_true")
    ap.add_argument("--reviewed-fingerprint", help="fingerprint of a diff already reviewed")
    ap.add_argument("--sample", action="store_true", help="run on a built-in example")
    ap.add_argument("--output", choices=["text", "json"], default="text")
    a = ap.parse_args()

    fp = None
    if a.sample:
        files, lines, paths, tests = SAMPLE["files"], SAMPLE["lines"], SAMPLE["paths"], True
    elif a.git:
        files, lines, paths, fp = from_git(a.git)
        tests = any(re.search(r"(test|spec)", p, re.I) for p in paths)
    elif a.files is not None and a.lines is not None:
        files, lines = a.files, a.lines
        paths = [p for p in (a.paths or "").split(",") if p]
        tests = a.tests_changed
    else:
        print("insufficient input: pass --git REPO, or --files N --lines N [--paths a,b]",
              file=sys.stderr)
        return 4

    res = decide(files, lines, paths, tests, fp, a.reviewed_fingerprint)
    res.update(files=files, lines=lines, fingerprint=fp)
    if a.output == "json":
        print(json.dumps(res, indent=2))
    else:
        print(f"verdict: {res['verdict']}  ({files} files, {lines} lines)")
        for r in res["reasons"]:
            print(f"  - {r}")
        if fp:
            print(f"  fingerprint: {fp}")
    return 3 if res["verdict"] == "NOTHING-TO-REVIEW" else 0


if __name__ == "__main__":
    sys.exit(main())
