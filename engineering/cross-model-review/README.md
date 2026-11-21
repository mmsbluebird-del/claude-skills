# cross-model-review

Get a second model's review of your change — and check it before you believe it.

A companion to [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc)
(Apache-2.0, © OpenAI), the official plugin that runs Codex from inside Claude Code.
That plugin supplies the runtime. This one supplies the judgement around it, in
three stdlib Python tools. **It calls no model, needs no API key, and includes none
of the upstream's code.** It also works with any other reviewer (Gemini, a second
Claude) because it only handles the text going in and the findings coming out.

| Tool | Job | Refuses (exit) |
|---|---|---|
| `review_gate.py` | SKIP / foreground / background / adversarial from size, risk paths and a diff fingerprint | empty change (3), no inputs (4) |
| `prompt_contract_builder.py` | block-structured prompt per job kind | vague task (3), bundled jobs (4) |
| `findings_verifier.py` | checks each finding's file, lines and quoted evidence on disk | any rejected finding or contradictory verdict (4) |

```bash
S=engineering/cross-model-review/skills/cross-model-review/scripts
python $S/review_gate.py --sample
python $S/prompt_contract_builder.py --sample
python $S/findings_verifier.py --sample      # exits 4 by design: one finding cites a missing file
```

Install upstream for Codex: `/plugin marketplace add openai/codex-plugin-cc`.
Using it needs a Codex CLI login with an OpenAI account; this plugin does not.

## Design decisions

1. **Companion, not vendor.** The upstream is a Node.js runtime that shells out to a
   paid-account CLI. Vendoring it would need an exception to this library's
   stdlib-Python and no-model-call rules. Linking to it costs nothing.
2. **Verification is the addition.** The upstream tells Claude to present findings
   verbatim. Verbatim is wrong when a reviewer cites a file that does not exist,
   so findings are checked against the tree first.
3. **The gate can say no.** A review nobody needed teaches people to ignore reviews.
4. **Present, then stop.** Kept from upstream: no auto-applied fixes.
5. **Original text.** Prompt blocks are written here, not copied.

## Limits

The verifier proves a quote and location exist, not that the reviewer's reasoning
is sound. A reviewer's `approve` is not a pass. Line numbers drift after edits.

## License

MIT (see `LICENSE`). Upstream remains Apache-2.0 under its own terms.
