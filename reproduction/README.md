# FTEC5660: SimpleMem reproducibility study

This coursework reproduces the text-memory pipeline of [SimpleMem](https://github.com/aiming-lab/SimpleMem) on a budgeted LoCoMo subset and measures one controlled modification: disabling reflective retrieval. The original authors retain credit for SimpleMem; their license and multilingual documentation are preserved.

## Completed experiment

Two complete conversations, 80 distinct questions, two conditions and three trials per condition produced **480 question-runs**. With reflection on/off, category-aware LoCoMo F1 was **48.56 / 48.28 points**. Disabling reflection reduced API tokens per question by **62.2%** and measured question latency by **42.1%** under the fixed paired workload. These are subset results with DeepSeek Flash, not a reproduction of the paper's full-benchmark numerical result.

## Submission materials

- [Final report: seven-page PDF](../output/pdf/SimpleMem_Reproducibility_Report.pdf).
- [Combined measured results](results/replication-20261109/RESULTS.md), [first-conversation results](results/formal-20261109/RESULTS.md), and [historical pilot](results/pilot-20261109/RESULTS.md).

The experiment and PDF report are complete. Repository publication and recording/submitting the presentation remain separate steps. Add any course-required student identity before final submission. Optional editable report, presentation and publishing drafts have been removed from the current tree at the owner's request.

## Sources and provenance

- SimpleMem source commit: `db80b6a7c591e0ea730a058e9f5fc4eb06572299`. All 461 downloaded files matched that upstream snapshot before local changes.
- LoCoMo data/scorer commit: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, from [snap-research/locomo](https://github.com/snap-research/locomo).
- Dataset SHA-256: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Exact embedding file versions/hashes: [provenance.json](provenance.json). Qwen's official ModelScope distribution was used after Hugging Face timed out; all downloaded files were hash-checked.
- Fixed designs: [original protocol](FORMAL_PROTOCOL.md), `formal_protocol.json`, `replication_plan.json`, and `replication_protocol.json`. These experimental manifests are preserved unchanged.

## Environment and installation

Measured on an Apple Silicon Mac with Python 3.13.2, torch 2.6.0 and transformers 4.57.0. Qwen/Qwen3-Embedding-0.6B ran on CPU with four threads during the formal experiments. The exact installed package snapshot is `requirements-lock.txt`; `requirements-text.txt` is the smaller text-pipeline dependency list. Other operating systems or Python versions may require package adjustments.

Run commands from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r reproduction/requirements-lock.txt
cp reproduction/config.template.py config.py
cp reproduction/deepseek.env.example .env
.venv/bin/python reproduction/setup_key.py
.venv/bin/python reproduction/download_data.py
.venv/bin/python reproduction/download_embedding.py
.venv/bin/python reproduction/check_setup.py --embedding
```

On this Mac, installation required the system certificate bundle. If the same certificate error occurs, prefix the installation command with `PIP_CERT=/etc/ssl/cert.pem SSL_CERT_FILE=/etc/ssl/cert.pem REQUESTS_CA_BUNDLE=/etc/ssl/cert.pem`. Keep TLS certificate verification enabled.

Create an API key in your own [DeepSeek account](https://platform.deepseek.com/). The setup tool accepts hidden input; the root `Configure_API_Key.command` is a double-click launcher after the environment is installed. Credentials remain in ignored `.env`; root `config.py` is also ignored. Do not commit either file. No key is needed merely to read the saved results.

Optional paid checks: `check_setup.py --api` sends one short request; `smoke_test.py` runs a tiny synthetic memory example. The recorded smoke test built two memories and answered Shanghai in 8.79 seconds, excluding initialization. It is not a benchmark result.

## Inspect or recompute saved results offline

The tracked result directories contain the raw answers, reference answers, per-request usage ledgers, scores, figures and memory snapshots. Reading these files does not invoke a model.

The analysis scripts read the original local `test_results/` run folders. Those temporary folders are ignored and are not included in a fresh clone. To recompute tables directly from a fresh clone's tracked archives, use:

```sh
.venv/bin/python reproduction/analyze_formal.py --archived
.venv/bin/python reproduction/analyze_replication.py --archived
```

Without `--archived`, analysis reads the original local run folders. Both modes are offline and preserve experimental evidence.

## Replay the paid experiment in a separate checkout

Restore the exact recorded memories without paid reconstruction:

```sh
.venv/bin/python reproduction/restore_formal_memory.py
.venv/bin/python reproduction/restore_replication_memory.py
```

Then run the question trials, which incur API charges:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/python -u reproduction/run_formal.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/python -u reproduction/run_replication.py
.venv/bin/python reproduction/analyze_formal.py
.venv/bin/python reproduction/analyze_replication.py
```

The runners resume the same persistent ledger and skip completed tuples. Use a separate checkout for an independent repeat; restarting must not reset the budget. The original experiment had a CNY 9 question-phase cap plus CNY 1 reserved for prior checks. The extension had a separate CNY 4.5 cap including memory construction and all queries. Prices and available model aliases can change: check the provider before a new paid run. Responses are stochastic and the provider alias is not an immutable model snapshot.

`run_replication.py --build-memory` reconstructs the extension memories using paid calls under the same extension ledger. Restoring the snapshot is sufficient to repeat retrieval and answers. To inspect pilot selection without API usage, run `run_pilot.py --dry-run`.

## Controlled settings and metrics

Both arms use the same fixed memory, model, prompts, planner and retrieval settings. Only reflection changes; the on arm permits at most two additional retrieval rounds. Each conversation contributes ten questions from each of categories 1-4. Category 5 is excluded. Each question's two arms run concurrently, with sequential retrieval inside each arm and serialized CPU embedding calls. Latency includes this shared workload.

The primary metric follows the pinned category-aware LoCoMo lexical F1 rules. The original SimpleMem set-token F1 is retained as a secondary metric. Neither is a semantic correctness rate. Mean and sample standard deviation are calculated across three trial aggregates. The question-paired bootstrap is conditional on these two fixed conversations and memories; it does not establish population generality or non-inferiority.

## Changes and debug diary

1. Downloaded and pinned missing benchmark data; recorded package/model provenance.
2. Fixed certificate configuration, installed missing `pylance==0.39.0` for keyword indexing, and verified the database backend.
3. Added an explicit DeepSeek thinking toggle and optional embedding device selection. CPU avoids a torch 2.6.0 Metal/MPS shape-inference crash on this Mac. These settings are shared by both arms.
4. Added fixed sampling, three-trial runners, official-rule scoring, persistent budget reservations, failure accounting and offline analysis. Original text pipeline prompts were retained.
5. Fixed a local extension warmup check that still searched for Caroline; it now uses the current conversation speaker. This happened before any extension question API calls. The 14 completed build calls, memories and budget ledger were retained.
6. Preserved raw experimental outputs and snapshots; translated only coursework prose, helper prompts and report generators. Upstream multilingual materials are unchanged.

## Cost and limitations

Metered pilot, formal and extension phases total 2,495 API calls and 4,265,887 tokens, with a price-list estimate of CNY 4.2078-8.4156. This excludes the initial connection check and synthetic smoke test and is not an invoice. No account balances are published.

Only two of ten LoCoMo conversations were tested. The extension conversation was chosen by a cost rule, not random sampling. Memories were built once per conversation. No paid semantic judge was used. The paper's GPT-4.1-mini full-benchmark F1 of 43.24 is contextual only: model, subset and code version differ.
