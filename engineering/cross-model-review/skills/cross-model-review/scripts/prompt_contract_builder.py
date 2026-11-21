#!/usr/bin/env python3
"""prompt_contract_builder.py — assemble a block-structured prompt for a second model.

Builds an XML-block prompt (task, output contract, follow-through, verification,
grounding, action safety) for one job kind, choosing blocks by what that job needs.
It writes text; it never calls a model.

It refuses rather than guesses:
  * a vague task such as "take a look" or "think harder" (exit 3) — prints the
    questions that would make it concrete;
  * a task that bundles unrelated jobs (exit 4) — review, fix, docs and roadmap are
    separate runs.

Standard library only.

Exit codes:
    0  prompt produced
    2  usage error
    3  task too vague
    4  task mixes unrelated jobs
"""
from __future__ import annotations

import argparse
import json
import re
import sys

BLOCKS = {
    "output": "<structured_output_contract>\nReturn exactly the requested shape and nothing else. Put the highest-value item first. Keep it compact.\n</structured_output_contract>",
    "follow": "<default_follow_through_policy>\nTake the most reasonable low-risk reading and keep going. Stop to ask only when a missing detail changes correctness, safety, or an irreversible action.\n</default_follow_through_policy>",
    "complete": "<completeness_contract>\nDo not stop at the first plausible answer. Check follow-on fixes, edge cases and cleanup the result needs.\n</completeness_contract>",
    "verify": "<verification_loop>\nBefore finalizing, check the result against the task and the files or tool output you observed. If a check fails, revise instead of reporting the first draft.\n</verification_loop>",
    "missing": "<missing_context_gating>\nDo not guess repository facts. Retrieve missing context with tools, or state exactly what remains unknown.\n</missing_context_gating>",
    "ground": "<grounding_rules>\nEvery claim must rest on the provided context or your tool output. Label inferences as inferences.\n</grounding_rules>",
    "dig": "<dig_deeper_nudge>\nAfter the first finding, look for a second-order failure: what breaks when this one is fixed or when it recurs?\n</dig_deeper_nudge>",
    "research": "<research_mode>\nSeparate what you observed from what you infer and from what is still open.\n</research_mode>",
    "cite": "<citation_rules>\nBack important claims with the specific source you inspected. Prefer primary sources.\n</citation_rules>",
    "safety": "<action_safety>\nKeep changes narrow. No unrelated refactors, renames or reformatting. List every file you touched.\n</action_safety>",
}
PLAN = {
    "review": ["output", "ground", "dig"],
    "adversarial-review": ["output", "ground", "dig"],
    "debug": ["output", "follow", "complete", "verify", "missing"],
    "implement": ["output", "follow", "complete", "verify", "missing", "safety"],
    "research": ["output", "research", "cite", "ground"],
}
STANCE = {
    "adversarial-review": "<operating_stance>\nDefault to skepticism. Try to find the strongest reasons this change should not ship yet. A change that only works on the happy path has a real weakness.\n</operating_stance>",
}
VAGUE = [r"\btake a look\b", r"\blet me know what you think\b", r"\bthink harder\b",
         r"\bbe (very )?smart\b", r"\bfix everything\b", r"\bmake it better\b",
         r"\bimprove (it|this)\b"]
JOBS = {"review": r"\breview\b|\baudit\b", "fix": r"\bfix\b|\bimplement\b|\bpatch\b",
        "docs": r"\bdocs?\b|\bdocument(ation)?\b|\breadme\b", "roadmap": r"\broadmap\b|\bplan the next\b"}
QUESTIONS = ["What exact artifact or failure is in scope (file, diff, error text)?",
             "What does done look like — a verdict, a root cause, a patch?",
             "Which one job is this run: review, debug, implement or research?"]


def build(kind: str, task: str, focus: str, write: bool) -> dict:
    words = len(task.split())
    if words < 8 or any(re.search(p, task, re.I) for p in VAGUE):
        return {"status": "vague", "questions": QUESTIONS}
    jobs = [j for j, p in JOBS.items() if re.search(p, task, re.I)]
    if len(jobs) >= 3 or (kind != "implement" and len(jobs) >= 2 and "fix" in jobs):
        return {"status": "mixed", "jobs": jobs,
                "advice": "Split into separate runs, one job each; feed the first result into the next."}
    parts = [f"<task>\n{task.strip()}\n" + (f"Focus: {focus.strip()}\n" if focus else "") + "</task>"]
    if kind in STANCE:
        parts.append(STANCE[kind])
    keys = list(PLAN[kind]) + (["safety"] if write and "safety" not in PLAN[kind] else [])
    for key in keys:
        if key == "safety" and not write:
            continue
        parts.append(BLOCKS[key])
    if not write and kind in ("review", "adversarial-review", "research", "debug"):
        parts.append("<action_safety>\nRead-only run. Do not edit files.\n</action_safety>")
    prompt = "\n\n".join(parts)
    warns = []
    if len(prompt.split()) > 350:
        warns.append("prompt exceeds ~350 words — trim redundant blocks before sending")
    return {"status": "ok", "kind": kind, "prompt": prompt, "words": len(prompt.split()),
            "blocks": [re.match(r"<(\w+)>", p).group(1) for p in parts], "warnings": warns}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kind", choices=sorted(PLAN), default="review")
    ap.add_argument("--task", help="the concrete job, with scope and expected end state")
    ap.add_argument("--task-file")
    ap.add_argument("--focus", default="")
    ap.add_argument("--write", action="store_true", help="the run may edit files")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--output", choices=["text", "json"], default="text")
    a = ap.parse_args()
    task = a.task or ""
    if a.task_file:
        task = open(a.task_file, encoding="utf-8").read()
    if a.sample:
        task = ("Review the staged changes to the retry logic in src/queue/worker.py for "
                "duplicate delivery and partial-failure bugs; return a ship or no-ship verdict.")
        a.kind = "adversarial-review"
    if not task.strip():
        print("no task given: pass --task or --task-file", file=sys.stderr)
        return 3
    res = build(a.kind, task, a.focus, a.write)
    if a.output == "json":
        print(json.dumps(res, indent=2))
    elif res["status"] == "ok":
        print(res["prompt"])
        for w in res["warnings"]:
            print(f"\nWARNING: {w}", file=sys.stderr)
    elif res["status"] == "vague":
        print("REFUSED (vague task). Answer these first:", file=sys.stderr)
        for q in res["questions"]:
            print(f"  - {q}", file=sys.stderr)
    else:
        print(f"REFUSED (mixed jobs: {', '.join(res['jobs'])}). {res['advice']}", file=sys.stderr)
    return {"ok": 0, "vague": 3, "mixed": 4}[res["status"]]


if __name__ == "__main__":
    sys.exit(main())
