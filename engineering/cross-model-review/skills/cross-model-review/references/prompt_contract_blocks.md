# Prompt contracts for a second model

Treat the reviewer like an operator, not a collaborator: a compact prompt in stable
XML blocks that states the job, the output shape, what to do by default, and how to
verify. This follows the method in the upstream plugin's `gpt-5-4-prompting` skill
(Apache-2.0); the block text here is original.

## Block matrix (what `prompt_contract_builder.py` emits)

| Job | Blocks |
|---|---|
| review | task, output contract, grounding, dig-deeper |
| adversarial-review | review blocks plus operating stance (skeptical) |
| debug | task, output contract, follow-through, completeness, verification, missing-context |
| implement | debug blocks plus action safety (narrow edits, list touched files) |
| research | task, output contract, research mode, citations, grounding |

A read-only run always gets a "do not edit files" safety block.

## Rules

1. One job per run. Review, fix, docs and roadmap are separate runs. 🟢 upstream guidance.
2. State the end state. A run without a defined "done" ends at the first plausible answer.
3. Tighten the contract before raising effort. 🟡 upstream guidance; plausible, not benchmarked here.
4. Ground every claim; label inference as inference.
5. Keep it under ~350 words; the builder warns past that.
6. For a follow-up on the same thread send only the delta.

## Anti-patterns the builder refuses

- Vague framing ("take a look", "think harder", "make it better") — exit 3.
- Bundled jobs (review + fix + docs) — exit 4.
- No output contract, no follow-through default, unsupported certainty — blocks added by default.

## Sources

1. openai/codex-plugin-cc, `skills/gpt-5-4-prompting/` SKILL.md and references (Apache-2.0).
2. Anthropic, "Building effective agents" (2024) — keep prompts simple; invest in tool and output design.
3. Anthropic prompt engineering docs — use XML tags to structure prompts (docs.anthropic.com).
4. Zheng et al., arXiv:2306.05685 — judge biases motivate an explicit output contract.
5. OpenAI, Codex documentation (developers.openai.com/codex) — the reviewer runtime these prompts target.
6. Anthropic, Claude Code documentation on plugins and subagents (docs.claude.com) — how the reviewer is wired in.
