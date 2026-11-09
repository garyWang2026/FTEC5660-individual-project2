"""Small baseline-only LoCoMo pilot. Persists usage after every API call; no judge model."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class PilotLimitReached(BaseException):
    """Escape upstream broad Exception handlers without generating repeated paid retries."""


def select_questions(sample, per_category=2, seed=5660):
    rng = random.Random(seed)
    selected = []
    for category in [1, 2, 3, 4]:
        available = [(i, q) for i, q in enumerate(sample['qa']) if q['category'] == category and q.get('answer') is not None]
        selected.extend(rng.sample(available, min(per_category, len(available))))
    return sorted(selected, key=lambda pair: pair[0])


def upstream_f1(prediction, reference):
    # Exact set-token F1 rule from upstream test_locomo10.py (not official LoCoMo F1).
    def tokens(s):
        return set(str(s).lower().replace('.', ' ').replace(',', ' ').replace('!', ' ').replace('?', ' ').split())
    a, b = tokens(prediction), tokens(reference)
    if not a or not b or not (a & b):
        return 0.0
    precision, recall = len(a & b) / len(a), len(a & b) / len(b)
    return 2 * precision * recall / (precision + recall)


def convert_dialogues(sample):
    from simplemem.core.models.memory_entry import Dialogue
    conversation = sample['conversation']
    keys = sorted([k for k, v in conversation.items() if k.startswith('session_') and isinstance(v, list)], key=lambda k: int(k.split('_')[1]))
    dialogues = []
    for key in keys:
        timestamp = conversation.get(key + '_date_time')
        if not timestamp:
            continue
        for turn in conversation[key]:
            text = turn.get('text', '')
            if 'img_url' in turn and 'blip_caption' in turn:
                text = f"[Image: {turn['blip_caption']}] {text}".strip()
            dialogues.append(Dialogue(dialogue_id=len(dialogues)+1, speaker=turn['speaker'], content=text, timestamp=timestamp))
    return dialogues


class UsageRecorder:
    def __init__(self, path, max_calls=80, max_tokens=250_000):
        self.path, self.max_calls, self.max_tokens = path, max_calls, max_tokens
        self.lock = threading.Lock()
        self.events, self.reserved_tokens = [], 0
        self.phase = 'build_memory'

    def wrap(self, create):
        def measured(**kwargs):
            if kwargs.get('stream'):
                raise PilotLimitReached('Pilot requires non-streaming responses for reliable usage logging.')
            # A deliberately generous byte-based reservation, not a tokenizer estimate used as a result.
            output_limit = 8192 if self.phase == 'build_memory' else 4096
            reserve = sum(len(m['content'].encode('utf-8')) + 128 for m in kwargs['messages']) + output_limit
            with self.lock:
                used = sum(e.get('total_tokens', 0) for e in self.events)
                if len(self.events) >= self.max_calls or used + self.reserved_tokens + reserve > self.max_tokens:
                    raise PilotLimitReached('Pilot call/token safety limit reached; partial results were saved.')
                self.reserved_tokens += reserve
                event = {'index': len(self.events), 'phase': self.phase, 'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'started', 'request_model': kwargs['model'], 'temperature': kwargs.get('temperature'), 'max_tokens': output_limit, 'prompt_sha256': hashlib.sha256(json.dumps(kwargs['messages'], sort_keys=True).encode()).hexdigest()}
                self.events.append(event)
            kwargs['max_tokens'] = output_limit
            start = time.perf_counter()
            try:
                response = create(**kwargs)
                usage = response.usage
                if usage is None:
                    raise PilotLimitReached('Provider returned no usage; pilot stopped rather than running unmetered.')
                raw = usage.model_dump()
                event.update({'status': 'ok', 'response_model': response.model, 'request_id': response.id, 'prompt_tokens': usage.prompt_tokens, 'completion_tokens': usage.completion_tokens, 'total_tokens': usage.total_tokens, 'cached_input_tokens': raw.get('prompt_cache_hit_tokens', (raw.get('prompt_tokens_details') or {}).get('cached_tokens', 0)) or 0, 'finish_reason': response.choices[0].finish_reason})
                if response.choices[0].finish_reason != 'stop':
                    raise PilotLimitReached('Unexpected/truncated model completion; pilot stopped for inspection.')
                return response
            except BaseException as exc:
                event['status'] = 'error'
                event['error_type'] = type(exc).__name__
                raise
            finally:
                event['duration_seconds'] = time.perf_counter() - start
                with self.lock:
                    self.reserved_tokens -= reserve
                    with self.path.open('a') as f:
                        f.write(json.dumps(event) + '\n')
        return measured

    def summary(self, events=None):
        events = self.events if events is None else events
        prompt = sum(e.get('prompt_tokens', 0) for e in events)
        output = sum(e.get('completion_tokens', 0) for e in events)
        cached = sum(e.get('cached_input_tokens', 0) for e in events)
        low = ((prompt-cached) * 1 + cached * 0.02 + output * 4) / 1_000_000
        return {'api_calls': len(events), 'failed_api_calls': sum(e['status'] != 'ok' for e in events), 'prompt_tokens': prompt, 'cached_input_tokens': cached, 'completion_tokens': output, 'total_tokens': prompt+output, 'estimated_cost_cny_off_peak': low, 'estimated_cost_cny_peak': 2*low, 'cost_note': 'Rate-card estimate for deepseek-flash, not an account invoice; lower/upper reflect off-peak/peak. 2026-11-09 official CNY rates.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--per-category', type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.per_category <= 2:
        raise SystemExit('Pilot limited to 1 or 2 questions per category.')
    data_path = ROOT / 'test_ref/locomo10.json'
    data = json.loads(data_path.read_text())
    sample = data[0]
    chosen = select_questions(sample, args.per_category)
    if args.dry_run:
        print(json.dumps({'sample_id': sample['sample_id'], 'question_indices': [i for i, _ in chosen], 'categories': dict(Counter(q['category'] for _, q in chosen)), 'questions': len(chosen)}, indent=2))
        return
    import config
    if not config.OPENAI_API_KEY:
        raise SystemExit('API key not configured.')
    if config.LLM_MODEL != 'deepseek-flash' or config.OPENAI_BASE_URL.rstrip('/') != 'https://api.deepseek.com':
        raise SystemExit('Pilot price accounting is configured only for the official deepseek-flash endpoint.')
    from main import SimpleMemSystem
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run = ROOT / 'test_results' / ('pilot-' + stamp)
    run.mkdir(parents=True, exist_ok=False)
    recorder = UsageRecorder(run/'api_usage.jsonl')
    meta = {'purpose': 'small baseline-only usage pilot, not a full reproduction', 'sample_id': sample['sample_id'], 'sample_index': 0, 'question_indices': [i for i, _ in chosen], 'selection_seed': 5660, 'per_category': args.per_category, 'model': config.LLM_MODEL, 'thinking': config.ENABLE_THINKING, 'streaming': False, 'reflection': True, 'planning': True, 'reflection_rounds': 2, 'embedding_device': config.EMBEDDING_DEVICE, 'metric': 'upstream set-token F1; not the official LoCoMo scorer', 'data_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(), 'git_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'price_source': 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/', 'price_verified_on': '2026-11-09', 'input_miss_cny_per_million_off_peak': 1, 'input_hit_cny_per_million_off_peak': 0.02, 'output_cny_per_million_off_peak': 4, 'api_max_output_tokens_build': 8192, 'api_max_output_tokens_query': 4096, 'max_api_calls': 80, 'max_pilot_tokens': 250_000}
    (run/'selection.json').write_text(json.dumps({'metadata': meta, 'questions': [{'qa_index':i, **q} for i,q in chosen]}, indent=2))
    system = SimpleMemSystem(db_path=str(run/'memory_db'), clear_db=False, enable_parallel_processing=True, max_parallel_workers=2, enable_parallel_retrieval=False, enable_planning=True, enable_reflection=True, use_streaming=False)
    system.llm_client.client = system.llm_client.client.with_options(timeout=90, max_retries=0)
    system.llm_client.client.chat.completions.create = recorder.wrap(system.llm_client.client.chat.completions.create)
    rows = []
    build_seconds = None
    completed = False
    try:
        dialogues = convert_dialogues(sample)
        meta['dialogue_turns'] = len(dialogues)
        start = time.perf_counter()
        system.add_dialogues(dialogues)
        system.finalize()
        build_seconds = time.perf_counter()-start
        memories = system.get_all_memories()
        if not memories:
            raise PilotLimitReached('No memories were built.')
        (run/'memories.json').write_text(json.dumps([m.model_dump() for m in memories], indent=2))
        meta['memory_count'] = len(memories)
        print(f'PILOT: memory ready: {len(memories)} entries, {build_seconds:.1f}s', flush=True)
        for j, (idx, qa) in enumerate(chosen):
            recorder.phase = f'question_{idx}'
            before = len(recorder.events)
            start = time.perf_counter()
            contexts = system.hybrid_retriever.retrieve(qa['question'])
            retrieval_seconds = time.perf_counter()-start
            start = time.perf_counter()
            answer = system.answer_generator.generate_answer(qa['question'], contexts)
            answer_seconds = time.perf_counter()-start
            usage = recorder.summary(recorder.events[before:])
            failed = usage['failed_api_calls'] > 0 or answer in ['Failed to generate answer', 'No relevant information found']
            row = {'qa_index':idx, 'question':qa['question'], 'reference':str(qa['answer']), 'answer':answer, 'category':qa['category'], 'retrieval_seconds':retrieval_seconds, 'answer_seconds':answer_seconds, 'total_seconds':retrieval_seconds+answer_seconds, 'retrieved_memories':len(contexts), 'retrieved_ids':[m.entry_id for m in contexts], 'failed':failed, 'upstream_f1':0.0 if failed else upstream_f1(answer, qa['answer']), 'usage':usage}
            rows.append(row)
            with (run/'questions.jsonl').open('a') as f:
                f.write(json.dumps(row)+'\n')
            print(f'PILOT: question {j+1}/{len(chosen)} finished; category {qa["category"]}; F1={row["upstream_f1"]:.3f}', flush=True)
        completed = True
    finally:
        summary = {'metadata':meta, 'completed':completed, 'completed_questions':len(rows), 'memory_build_seconds':build_seconds, 'usage':recorder.summary(), 'memory_build_usage':recorder.summary([e for e in recorder.events if e['phase']=='build_memory']), 'mean_upstream_f1':statistics.mean(r['upstream_f1'] for r in rows) if rows else None, 'mean_question_seconds':statistics.mean(r['total_seconds'] for r in rows) if rows else None, 'failed_questions':sum(r['failed'] for r in rows), 'result_dir':str(run)}
        (run/'summary.json').write_text(json.dumps(summary, indent=2))
        system.llm_client.client.close()
        print('PILOT SUMMARY', json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
