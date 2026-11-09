# Prespecified first-conversation experiment

Research question: How does disabling reflective retrieval change answer F1, API usage and latency on a fixed long-conversation memory?

- Task: 40 LoCoMo conv-26 questions, ten each from categories 1-4; exclude all eight pilot questions.
- Selection seed: 5660. The immutable question list is in `formal_protocol.json`, saved before execution.
- Only the reflection switch differs between arms. Model, prompts, retrieval settings, planning and all 454 fixed memory entries are shared.
- Three full trials per arm give 240 question-runs. No provider model seed is set; verbatim deterministic answers are not claimed.
- Run each question's two arms concurrently, at most two question-runs in flight; retrieval within an arm is sequential, embedding calls are serialized and CPU thread count is four. Reported latency is under this fixed shared workload.
- Question and arm submission order are randomized with a fixed schedule seed of 5661 + trial.
- Primary metric: pinned LoCoMo category-aware F1. Secondary metric: original SimpleMem set-token F1. Both are computed offline on all answers and do not alter model inputs.
- Official-rule normalization removes punctuation and a/an/the/and, applies Porter stemming and counts token multiplicity. Category 1 averages best matches for comma-separated reference subanswers; category 3 uses the reference prefix before the semicolon; categories 2/4 use direct scoring.
- [Pinned scoring source](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py).
- Persist a cost reservation before each request and record returned usage. Missing usage or truncated output stops the run. Interrupted or unknown requests retain their full reservation.
- Original total cap: CNY 10, comprising CNY 1 reserved for prior pilot/checks and CNY 9 for formal queries at peak prices. Conservatively reserve input UTF-8 bytes plus template overhead and up to 4096 output tokens before sending each request. Stop and save if the next request cannot be covered.
- Peak rates checked on 2026-11-09, CNY per million tokens: uncached input 2, cached input 0.04, output 8. Report off-peak/peak estimates; actual billing may differ.
- Resume using the same ledger. Completed tuples are skipped, and restarting cannot reset expenditure.
- Use a copied memory database without rebuilding it; verify all memory content and IDs are unchanged at completion.
- Aggregate each 40-question trial, then report the mean and sample standard deviation across three trials. Report categories separately; retain failed questions with zero scores and count failures separately.
- Variability concerns retrieval/answer generation conditional on fixed memories. A single conversation cannot establish whole-LoCoMo performance.
- The paper's Table 1 GPT-4.1-mini macro F1 of 43.24 is contextual only. DeepSeek, a conversation subset and newer source code prevent direct numerical reproduction claims.

Preparation without API calls: `.venv/bin/python reproduction/run_formal.py --prepare`.

Paid run/resume: `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -u reproduction/run_formal.py`.

Local progress and ledger: `test_results/formal-20261109`. Questions and scoring were not changed during execution. The separately fixed second-conversation design is in `replication_plan.json` and `replication_protocol.json`.
