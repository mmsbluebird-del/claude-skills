---
name: cross-model-review
description: Use before merging non-trivial changes, when stuck on a bug after two attempts, or when asked for a second opinion from another model (Codex, Gemini, a second Claude) — decides whether a cross-model review is worth running, builds the prompt contract, and verifies the reviewer's findings against the real files before presenting them.
argument-hint: "[optional: --git REPO | a review or rescue task]"
license: MIT
metadata:
  version: 1.0.0
  build_pattern: "Companion to openai/codex-plugin-cc (Apache-2.0): gate → prompt contract → verify findings → present then stop. Ships no upstream code and no runtime."
  distinct_from: "adversarial-reviewer (Claude reviews with a hostile stance; this brokers a different model); self-eval (grades this session); skill-doctor (grades past sessions)"
---

# cross-model-review — get a second model's opinion without trusting it blindly

A different model catches different mistakes, but its output is unverified text.
This skill runs the three steps the upstream Codex plugin leaves to the human.
It calls no model and needs no key: you invoke the reviewer yourself (for Codex,
install [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc)).

## Workflow

1. **Gate.** `python scripts/review_gate.py --git .` returns SKIP,
   RUN-FOREGROUND, RUN-BACKGROUND or RUN-ADVERSARIAL (risk paths: auth, money,
   migrations, secrets, infra, concurrency). Exit 3 = nothing to review. Respect SKIP.
2. **Contract.** `python scripts/prompt_contract_builder.py --kind review --task "..."`.
   Exit 3 = vague task, exit 4 = mixed jobs; answer the printed questions or split
   the run. One job per run. Use the reviewer's built-in review command for plain
   diff review and this builder for debugging, research and custom focus.
3. **Run the reviewer** (Codex: `/codex:review`, `/codex:adversarial-review`,
   `/codex:rescue`). Ask for JSON findings with `file`, `line_start`, `line_end`
   and a verbatim `evidence` quote (`assets/findings.example.json`).
4. **Verify.** `python scripts/findings_verifier.py findings.json --repo .`
   Exit 4 = a finding cites a missing file, out-of-range lines, or a quote not in
   the code. Drop REJECTED findings and say how many were dropped.
5. **Present, then stop.** Findings by severity, inference kept distinct from
   fact. Do not edit a file until the user picks which findings to fix.

Worked example:

```bash
S=engineering/cross-model-review/skills/cross-model-review/scripts
python $S/review_gate.py --git .            # RUN-ADVERSARIAL (auth path touched)
python $S/prompt_contract_builder.py --kind adversarial-review \
  --task "Review the session-token refresh change in src/auth/session.py for replay and expiry bugs; return ship or no-ship."
python $S/findings_verifier.py findings.json --repo .   # exit 4 -> drop REJECTED, report the count
```

## Hard rules

- Never turn a failed or unavailable reviewer into your own answer — report it.
- Never auto-apply review fixes, however obvious.
- A reviewer's `approve` is not a pass: the gate cannot see what it did not read.
- Do not send secrets or unreleased customer data to a third-party model; confirm first.
- Escalate effort only after tightening the prompt contract.

## Forcing questions

1. What would change my decision if the reviewer found something? If nothing, skip.
2. Which one job is this run: review, debug, implement or research?
3. Which files must the reviewer read, and does it have them?
4. May this code leave the machine for a third-party model?

## References

- `references/second_model_evidence.md` — when a second model helps and when it does not
- `references/prompt_contract_blocks.md` — the block method and per-job block matrix
- `references/findings_handling.md` — verify, order, present, stop
