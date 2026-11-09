## Interpretation

Token savings were approximately 62.2% and 62.1% in the two conversations. Mean F1 decreased by 0.15 and 0.41 points respectively, or 0.28 points combined. The efficiency pattern therefore appeared again in an independent conversation, conditional on this setup. The interval crosses zero and does not prove non-inferiority or universal superiority. The extension strengthens the coursework analysis but remains far smaller than the full benchmark.

## Extension debug diary

The first local query startup check still searched for the original conversation's speaker, Caroline, and failed on the new database. No extension evaluation-question API calls had been sent. All 14 completed memory-build calls, the resulting database and the persistent ledger were retained.

The warmup keyword was changed to the current conversation's `speaker_a`. This affects only an untimed local health check, not the fixed questions, scoring, model settings or arm difference. The corrected code version and protocol were saved before question trials began. Offline checks verified the 8192-token construction reservation and concurrent budget protection. The local startup failure is distinguished from API failures; no incomplete question was reported as completed.

## Restoration and replay

`fixed_memories.jsonl`, `memory_db_snapshot.zip` and `snapshot_manifest.jsonl` preserve the same 540 benchmark-derived memories and vectors/indexes, without credentials. After environment, data and model setup, run `.venv/bin/python reproduction/restore_replication_memory.py` to restore without paid construction. Use `reproduction/run_replication.py` for a paid question replay, or `reproduction/analyze_replication.py --archived` for offline combined analysis.

The original first-conversation results and fixed designs remain intact. An independent paid repeat should use a separate checkout and preserve its own persistent ledger. The current completed local tuples are skipped. Only metered tokens and price-list cost estimates are published, never API credentials or account balances.
