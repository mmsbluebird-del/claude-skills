---
description: Decide in one step whether a second-model review of the current change is worth running (SKIP / foreground / background / adversarial).
argument-hint: "[optional: repo path]"
---

# /cs:review-gate

```bash
python engineering/cross-model-review/skills/cross-model-review/scripts/review_gate.py --git "${ARGUMENTS:-.}"
```

Tell the user the verdict, the reasons, and the diff fingerprint. If the verdict is
SKIP, stop. If it is RUN-*, offer `/cs:cross-model-review`. Exit 3 means there is
nothing to review.
