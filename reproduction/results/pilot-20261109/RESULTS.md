# SimpleMem: historical eight-question usage pilot

Date: 2026-11-09. This pilot preceded the formal three-trial ablation. It is retained as a cost estimate and debugging record, not pooled into the formal quality result.

## Scope and settings

Full conv-26 input: 419 dialogue turns, including existing image captions but no QA gold answers or evidence labels. Two questions per category 1-4 were selected with seed 5660, indices 3, 9, 27, 30, 31, 56, 139 and 151. Category 5 was excluded. DeepSeek Flash ran with thinking disabled, planning and reflection enabled (at most two reflection rounds). Qwen3-Embedding-0.6B ran on CPU.

Memory construction used two workers; questions and retrieval were sequential. Output caps were 8192 tokens for construction and 4096 for retrieval/answers. SDK automatic retries were disabled. All requests completed normally, without truncation.

## Measured usage

| Measure | Memory construction | Eight questions | Total |
|---|---:|---:|---:|
| API calls | 11 | 52 | 63 |
| Input tokens | 29,480 | 100,372 | 129,852 |
| Output tokens | 60,554 | 6,379 | 66,933 |
| Total tokens | 90,034 | 106,751 | 196,785 |
| Off-peak estimate, CNY | 0.2717 | 0.1072 | 0.3789 |
| Peak estimate, CNY | 0.5434 | 0.2144 | 0.7578 |

Cached input totaled 19,072 tokens and was priced separately. Construction took 188.01 seconds and produced 454 memories. Mean retrieval-plus-answer latency was 11.61 seconds, excluding initial model loading. API and question failures: zero.

Costs use actual returned usage and the [official price list](https://api-docs.deepseek.com/quick_start/pricing/) checked on 2026-11-09, not a platform invoice. Off-peak rates per million tokens were CNY 0.02 cached input, 1 uncached input and 4 output; peak rates were double. Initial connectivity and synthetic smoke checks are excluded.

## Preliminary observations and subsequent decision

Mean original SimpleMem set-token F1 was 0.5224. This is lexical overlap, not 52.24% correct answers. Two responses exactly matched the reference text; others were partial or included an incorrect date. A writing-career answer and its reference both leaned negative but received zero under the original lexical scorer, motivating explicit scoring documentation for the formal study.

The one-trial, eight-question pilot used a different model and a tiny subset, so it cannot establish the paper's full-benchmark result. A linear projection for 40 questions, two conditions and three trials was CNY 3.22-6.43 for queries, plus CNY 0.27-0.54 if rebuilding memory. This was an estimate, not a spending guarantee. The subsequent formal study used a persistent budget ledger and reused these memories; all eight pilot questions were excluded from formal evaluation.

## Traceable artifacts

- `questions.csv`: original answers, references, scores, time and usage.
- `api_usage.jsonl`: all 63 metered calls, cache usage, timing, stage and status; no credentials.
- `summary.jsonl`: parameters, data hash, code version and aggregate results.
- The local memory database is retained under the ignored original pilot run directory; the formal result directory publishes its reusable snapshot.
- Sources: [LoCoMo](https://github.com/snap-research/locomo), [SimpleMem](https://github.com/aiming-lab/SimpleMem).
