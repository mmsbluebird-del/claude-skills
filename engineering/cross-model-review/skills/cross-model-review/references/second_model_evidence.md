# When a second model earns its cost

Confidence: 🟢 published result, 🟡 plausible and partly supported, 🔴 folklore.

## Claims

1. **A model reviewing its own output is a weak check.** 🟢 Huang et al. (2023)
   found that models asked to self-correct reasoning without external feedback
   often do not improve and can get worse. Panickssery et al. (2024) found models
   recognize and favor their own generations when judging. Both argue for a
   reviewer that is not the author.
2. **A different model is a different error profile, not a better one.** 🟡
   Multi-model setups (Du et al. 2023, multiagent debate; Wang et al. 2024,
   Mixture-of-Agents) report gains from combining models, but the gains depend on
   task and aggregation. Treat a second model as another noisy reader.
3. **Judge models have biases.** 🟢 Zheng et al. (2023) document position, verbosity
   and self-enhancement bias in LLM judges. A confident, long finding is not more
   likely to be right.
4. **Review is most valuable where defects are expensive and hard to see.** 🟡
   Google's engineering practices guide frames review around design, correctness,
   tests and complexity, with the goal that code health improves. Risk paths (auth,
   money, migrations) are where a miss costs most, which is why `review_gate.py`
   escalates on them.
5. **Reviewer output must be checkable.** 🟡 A finding with a file, line range and
   quote can be checked mechanically; one without cannot. That is the design
   reason `findings_verifier.py` exists.
6. **Cross-model review is a substitute for tests.** 🔴 It is not. It finds
   candidates for tests; it does not replace running them.

## Decision rule

Run a second model when the change is non-trivial, touches a risk path, or you are
stuck after two attempts. Skip it for docs-only edits, trivial diffs, and a diff
already reviewed at the same fingerprint.

## Sources

1. Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet", arXiv:2310.01798 (2023).
2. Panickssery, Bowman, Feng, "LLM Evaluators Recognize and Favor Their Own Generations", arXiv:2404.13076 (2024).
3. Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", arXiv:2306.05685 (2023).
4. Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate", arXiv:2305.14325 (2023).
5. Wang et al., "Mixture-of-Agents Enhances Large Language Model Capabilities", arXiv:2406.04692 (2024).
6. Google Engineering Practices, "Code Review Developer Guide", google.github.io/eng-practices/review.
7. openai/codex-plugin-cc README and `plugins/codex/commands/` (Apache-2.0), read at commit db52e28.
