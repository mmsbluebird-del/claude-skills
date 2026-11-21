# Handling a second model's findings

## Verify before presenting

`findings_verifier.py` checks each finding against the working tree.

| Status | Meaning | Action |
|---|---|---|
| VERIFIED | file and lines exist and the `evidence` quote is in the cited range (±2 lines) | present |
| LOCATED | file and lines exist, no quote supplied | present, mark "unverified claim" |
| REJECTED | missing file, bad range, path escape, or quote not found | drop; report the count |

A verdict that contradicts the findings (approve with a critical finding, or
needs-attention with none) also exits 4. The gate checks that evidence exists; it
cannot check that the reasoning from it is right.

## Present, then stop

1. Findings first, ordered by severity, using the reviewer's file:line exactly.
2. Keep facts, inferences and open questions distinct.
3. If there are no findings, say so and keep the residual-risk note short.
4. If the reviewer edited files, say so and list them.
5. **Stop.** Ask which findings, if any, to fix. Auto-applying review fixes is
   forbidden even when the fix is obvious.
6. If the reviewer failed or was never invoked, report that. Do not substitute a
   Claude-side answer.

## Staleness

Line numbers drift if files change after the review. Re-run the verifier after any edit.

## Sources

1. openai/codex-plugin-cc, `skills/codex-result-handling/SKILL.md` (Apache-2.0).
2. openai/codex-plugin-cc, `schemas/review-output.schema.json` — the finding shape accepted here.
3. Google, "Code Review Developer Guide" — reviewers comment on the code, authors decide.
4. Panickssery et al., arXiv:2404.13076 — why a model's own assessment is not evidence.
5. Fagan, "Design and code inspections to reduce errors in program development", IBM Systems Journal 15(3), 1976.
6. Bacchelli & Bird, "Expectations, outcomes, and challenges of modern code review", ICSE 2013.
