# SimpleMem: first-conversation reproduction and reflection ablation

Date: 2026-11-09. Completed 40 held-out questions x 2 conditions x 3 trials = 240 question-runs.

## Main results

| Metric (mean +/- sample SD across three trial aggregates) | Reflection on | Reflection off |
|---|---:|---:|
| Category-aware LoCoMo F1, 0-100 | 50.62 ± 2.53 | 50.47 ± 2.86 |
| Original SimpleMem set-token F1, 0-100 | 41.27 ± 1.77 | 40.83 ± 2.85 |
| All API tokens per question | 11691.64 ± 306.73 | 4418.64 ± 59.65 |
| API calls per question | 6.07 ± 0.06 | 4.00 ± 0.00 |
| Retrieval-plus-answer time, seconds | 9.82 ± 0.33 | 5.79 ± 0.17 |

Off minus on: -0.15 F1 points. Disabling reflection reduced tokens by 62.2%, API calls by 34.1% and latency by 41.0%.
After averaging three trials per question, 10,000 paired question bootstrap samples give a conditional interval of [-3.52, +3.06] F1 points. This describes this fixed conversation and memory, excludes memory-build variability, and is not a whole-benchmark confidence claim.

![Quality, token usage and latency](comparison.png)

## Category results

| Category | Reflection on F1 | Reflection off F1 |
|---|---:|---:|
| 1: Multi-hop | 32.22 +/- 5.46 | 29.04 +/- 1.56 |
| 2: Temporal | 73.42 +/- 3.60 | 74.24 +/- 4.19 |
| 3: Open-domain | 28.46 +/- 1.43 | 28.34 +/- 1.40 |
| 4: Single-hop | 68.38 +/- 1.78 | 70.26 +/- 4.73 |

## Usage and integrity checks

API calls: 1,208; input tokens: 1,803,810; output tokens: 129,424; total tokens: 1,933,234; cached input: 624,376.
Price-list estimate: CNY 1.7096-3.4192, within the CNY 9 formal cap (plus CNY 1 reserved for earlier checks). This is not an invoice. Unknown reservations: CNY 0.0000.
Failed/unknown API calls: 0; failed question-runs: 0. Failed questions are retained with zero scores. All 240 prescribed unique tuples and category counts were verified; question-level usage matches the ledger. All 454 memory contents and IDs remained unchanged. QA gold/evidence labels were not used to build or retrieve memories.

## Conditions and scope

- Text pipeline from SimpleMem db80b6a plus documented compatibility changes. Exact runtime and protocol: `run_metadata.jsonl`.
- DeepSeek Flash, thinking disabled, planning enabled. Only reflection differs; reflection on permits at most two extra retrieval rounds.
- Complete conv-26 input: 419 turns, 454 pilot-built memories. Ten held-out questions per category 1-4; all eight pilot questions excluded. Selection was fixed before formal answers.
- Qwen3-Embedding-0.6B on CPU, four threads. Two arms run concurrently; retrieval inside each arm is sequential. Timing describes shared load, not isolated single-request latency.
- Output cap 4096 tokens/request; SDK retries zero; timeout 90 seconds. Original application retry logic is retained and every request is metered.
- Primary scoring follows the pinned LoCoMo category-aware rules; original set-token F1 is secondary. Neither is semantic accuracy. Trial means are averaged across three trials; equal category counts make the overall mean equal to the category macro-average.

## Comparison with the reported paper result

Paper Table 1 reports GPT-4.1-mini F1 of 43.46 multi-hop, 58.62 temporal, 19.76 open-domain and 51.12 single-hop, macro-average 43.24. Our reflection-on subset F1 is 50.62. Different model, subset and source version prevent a direct numerical reproduction or superiority claim. Our tokens include planning, reflection and final answers; the paper's token accounting must be reconciled before calculating a cross-study saving ratio.

## Files and references

- `questions.csv` / `questions.jsonl`: raw answers, references, both scores, timings, usage and failure flags.
- `trials.csv`, `categories.csv`, `paired_questions.csv`: trial/category/paired aggregates.
- `api_ledger.jsonl`: persistent pre-request reservations and returned usage, without credentials.
- `run_metadata.jsonl`: fixed selection, protocol, code/data/memory hashes and runtime state.
- `analysis.jsonl`, `comparison.png`, `comparison.svg`: numerical analysis and figures.
- [Paper](https://arxiv.org/html/2601.02553v3), [SimpleMem](https://github.com/aiming-lab/SimpleMem), [pinned LoCoMo scorer](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py), [official pricing](https://api-docs.deepseek.com/quick_start/pricing/).

## Interpretation and qualitative checks

Disabling reflection reduced tokens and calls substantially while mean F1 decreased by 0.15 points on this fixed subset. The conditional paired interval crosses zero; it establishes neither a definite quality improvement nor an absence of quality loss. Averaging three trials per question, ten questions scored higher without reflection, eight lower and 22 tied.

Question 24 asks how Melanie relieves stress; the reference is "Running, pottery". In trial 1, reflection off answered "She runs." (F1 0.333), while reflection on included running and pottery (F1 1.000), together with additional activities. Reflection can recover relevant missing information.

Question 32 asks which LGBTQ+ events Caroline attended. In trial 1, reflection on produced a longer list with dates and F1 0.340; reflection off produced a shorter answer with F1 0.600. Differences reflect both retrieval and the lexical matching procedure. The category-aware multi-answer scorer weakly penalizes extra listed items. A perfect score does not guarantee all additional details are true.

No paid semantic judge was added. Raw answers are preserved for manual assessment.

## Restore the same fixed memory

`fixed_memories.jsonl`, `memory_db_snapshot.zip` and `snapshot_manifest.jsonl` preserve the 454 benchmark-derived memory entries, vectors and indexes without API credentials. After installing dependencies, configuration, data and the embedding model in a fresh checkout, run `.venv/bin/python reproduction/restore_formal_memory.py`, then the paid `reproduction/run_formal.py` runner. Restoration itself makes no model calls.

Use `reproduction/analyze_formal.py --archived` to regenerate this report, tables and figure offline from the tracked archives. These qualitative notes are retained separately from generated numerical summaries.
