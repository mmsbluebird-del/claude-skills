---
description: Gate, prompt-contract and verify a second-model review (Codex, Gemini, another Claude) of the current change, then present findings without editing code.
argument-hint: "[optional: --git REPO | the task for the reviewer]"
---

# /cs:cross-model-review

Run the cross-model-review workflow with `$ARGUMENTS`.

Load `engineering/cross-model-review/skills/cross-model-review/SKILL.md` and follow it.

```bash
S=engineering/cross-model-review/skills/cross-model-review/scripts
python $S/review_gate.py --git .
python $S/prompt_contract_builder.py --kind review --task "<concrete task>"
# run the reviewer yourself, save its JSON findings to findings.json
python $S/findings_verifier.py findings.json --repo .
```

Report every non-zero exit as a finding: exit 3 from the gate means nothing to
review, exit 3/4 from the builder means the task was vague or bundled, exit 4 from the
verifier means findings were rejected. Present verified findings by severity, then
ask which to fix. Do not edit files first.
