# SimpleMem reproducibility presentation

Presenter account: garyWang2026. Target: approximately 10-12 minutes, including a short repository walkthrough; maximum allowed: 15 minutes. This is an outline and speaking script, not a recording or a finished slide deck. Read the report and practice in your own words before recording in Zoom.

## Slide 1 - What I attempted (0:00-1:00)

Show: report title and the research question.

Hello. This project investigates SimpleMem, an agentic memory system for answering questions about long conversations. Instead of sending the entire conversation directly for every question, the system builds structured memories, searches those memories, optionally reflects on missing information, and then answers.

My target was to get the authors' text-memory pipeline running and reproduce its question-answering behavior on a meaningful subset of LoCoMo. I then tested one small change: turning reflective retrieval off while keeping the planner and memory fixed. I measured answer F1, tokens, API calls and elapsed time. I did not attempt the entire benchmark or the multimodal parts of the repository.

## Slide 2 - Sources and setup (1:00-2:15)

Show: report page 2 or a source/setup table.

I started from the authors' downloaded GitHub code. The initial 461 files matched the recorded upstream snapshot. I pinned the LoCoMo dataset and scoring source and recorded checksums so the inputs are traceable.

The underlying language model was DeepSeek Flash, accessed through the official endpoint. Thinking was explicitly disabled. Both experimental arms used the same model and prompts. The local embedding model was Qwen3-Embedding-0.6B on CPU. The setup used an Apple Silicon Mac and a separate Python environment.

There were several practical blockers. Certificate settings affected package downloads. A missing indexing dependency prevented keyword search. Hugging Face timed out, so I downloaded the official Qwen files from ModelScope and checked their hashes. A Metal backend crash led to CPU embeddings. These are documented compatibility choices, shared by both arms, rather than experimental variables.

## Slide 3 - From smoke test to fixed evaluation (2:15-3:30)

Show: report page 3, conversation table.

I first ran a small synthetic test. The system built two memories and correctly answered that Alice moved to Shanghai. That only confirmed the pipeline worked; it was not benchmark evidence.

Next, an eight-question pilot estimated API usage. It used the complete first conversation and produced 454 memories. All eight pilot questions were excluded from the later formal evaluation.

The final study used two complete conversations. The first had 419 dialogue turns and the second had 509. Each contributed 40 evaluation questions: ten from each of four categories. With two conditions and three trials, that produced 480 question-runs from 80 distinct questions. The second conversation was selected by a prespecified low-cost rule among eligible unused conversations, not because of its result. This improves coverage but does not make the sample representative of the full benchmark.

## Slide 4 - The controlled change and scoring (3:30-4:45)

Show: simple pipeline, with reflection highlighted.

The two arms shared the same stored memories, planner, prompts, model and retrieval settings. Only the reflection switch differed. With reflection on, the system could perform up to two supplementary retrieval rounds when it judged information incomplete. With reflection off, it answered without that loop.

The primary quality measure followed the pinned official LoCoMo lexical F1 rules, including category-specific handling. I also retained the authors' original set-token F1 as a secondary measure. Neither score is the percentage of answers that are factually correct.

I aggregated all questions within each trial and reported the mean and sample standard deviation across three trials. I also calculated a paired question bootstrap interval after averaging each question across trials. This interval is conditional on these two conversations and their fixed memories; it does not account for choosing new conversations or rebuilding memory.

## Slide 5 - Main measured results (4:45-6:15)

Show: `reproduction/results/replication-20261109/comparison.png` and report page 4.

With reflection on, combined LoCoMo F1 was 48.56 points. With reflection off, it was 48.28. The observed difference was minus 0.28 points. The conditional paired interval ran from minus 2.55 to plus 1.94, crossing zero. Therefore, I cannot claim that quality is guaranteed to stay the same.

The resource difference was much larger. Average API tokens per question fell from approximately 11,984 to 4,534, a reduction of 62.2 percent. Calls fell from about 6.08 to 4.00 per question. Measured retrieval-plus-answer time fell from 10.43 to 6.03 seconds, a reduction of 42.1 percent.

Both conversations showed roughly 62 percent token savings, so the efficiency pattern appeared again in the extension. All 480 prescribed runs completed, with zero API failures and no failed question-runs. Timing was measured with both arms running concurrently on the same machine, so these seconds describe shared load rather than isolated request latency.

## Slide 6 - What F1 can hide (6:15-7:30)

Show: the two qualitative examples on report page 5.

Reflection sometimes helped. One question asked how Melanie relieves stress. The reference contained running and pottery. In the first trial, reflection off mentioned running only; reflection on recovered both activities and obtained a higher score.

Another question asked which LGBTQ+ events Caroline attended. The reflection-on answer was longer and listed events and dates, but the shorter reflection-off answer received a higher lexical score. This shows that score differences depend on both retrieved content and the matching rules.

The multi-answer scorer can weakly penalize extra listed items. A perfect F1 therefore does not prove that every additional detail is true. I preserved raw answers so readers can inspect them. I did not add a paid semantic judge or claim a comprehensive factuality audit.

## Slide 7 - Costs and debugging (7:30-8:45)

Show: report page 6.

The metered pilot and two experimental phases used about 4.27 million tokens across 2,495 API calls. Applying the recorded off-peak and peak rates gives an estimate of about 4.21 to 8.42 yuan. This is an estimate, not a platform invoice, and it excludes the initial connection and synthetic checks.

A persistent ledger reserved a conservative cost before each request. Unknown usage kept its reservation, and resuming the run reused the same ledger. This made spending and retries auditable.

One extension startup failed because the local warmup still searched for the old speaker's name. This happened before any new evaluation-question calls. I fixed the keyword to use the current speaker and kept the already built memories and their 14 charged construction requests. That local failure is documented separately from the zero API failure count.

## Slide 8 - Repository walkthrough (8:45-10:00)

Show: saved files only. Do not run the paid runners during recording.

Here is the coursework README with installation and replay instructions. The original and extension result folders contain raw answers, scores, request ledgers and figures. The combined CSV has all 480 runs. Frozen protocols preserve the selected questions and settings.

The repository also includes snapshots of the exact memories and indexes. A new user can restore them without paying for construction, then repeat question answering with their own API account. Offline archive analysis can regenerate the statistics from tracked evidence without an API key. Local credentials and large model files are excluded from Git, and the original license and attribution remain.

For the demonstration, I will open the combined result table, the plot and one raw answer example. I will not display the local credential file.

## Slide 9 - Conclusions and limits (10:00-11:00)

Show: three concise takeaways.

First, the text-memory pipeline ran and produced measurable long-conversation question-answering behavior in the documented setup. Second, disabling reflection repeatedly reduced token use substantially, with a small observed mean lexical F1 decrease in this subset. Third, transparent provenance, scoring and budget accounting were essential to interpreting the result.

The paper reports a GPT-4.1-mini macro F1 of 43.24. My result is not directly comparable because the model, subset and source version differ. I cannot claim to have reproduced that numerical result or surpassed the paper.

A stronger follow-up would evaluate more independent conversations, repeat memory construction and assess factual correctness alongside lexical overlap. Within the current budget, this study provides a controlled and traceable account of what worked, what changed and what remains uncertain. Thank you.

## Recording checklist

- Add your course-required name/student ID to the opening slide or report as needed.
- Open the report, combined figure, README and raw example before starting Zoom.
- Record your own explanation; keep the final recording below 15 minutes.
- Confirm the recording has audible narration and readable shared-screen content.
- Save/share the recording using the course's accepted method and check instructor access.
- Submit its actual link with the report and published repository URL. No presentation URL exists until you record and share it.
