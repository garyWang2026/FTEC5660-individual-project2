## Interpretation and qualitative checks

Disabling reflection reduced tokens and calls substantially while mean F1 decreased by 0.15 points on this fixed subset. The conditional paired interval crosses zero; it establishes neither a definite quality improvement nor an absence of quality loss. Averaging three trials per question, ten questions scored higher without reflection, eight lower and 22 tied.

Question 24 asks how Melanie relieves stress; the reference is "Running, pottery". In trial 1, reflection off answered "She runs." (F1 0.333), while reflection on included running and pottery (F1 1.000), together with additional activities. Reflection can recover relevant missing information.

Question 32 asks which LGBTQ+ events Caroline attended. In trial 1, reflection on produced a longer list with dates and F1 0.340; reflection off produced a shorter answer with F1 0.600. Differences reflect both retrieval and the lexical matching procedure. The category-aware multi-answer scorer weakly penalizes extra listed items. A perfect score does not guarantee all additional details are true.

No paid semantic judge was added. Raw answers are preserved for manual assessment.

## Restore the same fixed memory

`fixed_memories.jsonl`, `memory_db_snapshot.zip` and `snapshot_manifest.jsonl` preserve the 454 benchmark-derived memory entries, vectors and indexes without API credentials. After installing dependencies, configuration, data and the embedding model in a fresh checkout, run `.venv/bin/python reproduction/restore_formal_memory.py`, then the paid `reproduction/run_formal.py` runner. Restoration itself makes no model calls.

Use `reproduction/analyze_formal.py --archived` to regenerate this report, tables and figure offline from the tracked archives. These qualitative notes are retained separately from generated numerical summaries.
