"""Tiny real end-to-end demo; requires credentials and incurs API usage. Not a benchmark."""
import sys, json, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
if not config.OPENAI_API_KEY:
    raise SystemExit('请先双击“配置模型密钥.command”，在本机输入密钥。')
from main import SimpleMemSystem
with tempfile.TemporaryDirectory(prefix='simplemem-smoke-') as db:
    system = SimpleMemSystem(db_path=db, clear_db=False, enable_parallel_processing=False, enable_parallel_retrieval=False)
    start = time.perf_counter()
    system.add_dialogue('Alice', 'I moved to Shanghai on 3 November 2026.', '2026-11-04T09:00:00')
    system.add_dialogue('Bob', 'I will visit you in Shanghai next month.', '2026-11-04T09:01:00')
    system.finalize()
    memories = system.get_all_memories()
    if not memories:
        raise SystemExit('No memories built; smoke test failed.')
    answer = system.ask('Which city did Alice move to?')
    result = {'purpose': 'synthetic smoke test, not a LoCoMo result', 'model': config.LLM_MODEL, 'question': 'Which city did Alice move to?', 'answer': answer, 'expected': 'Shanghai', 'contains_expected_city': 'shanghai' in answer.lower(), 'memory_count': len(memories), 'elapsed_seconds': time.perf_counter()-start}
    folder = ROOT / 'test_results'
    folder.mkdir(exist_ok=True)
    path = folder / ('smoke-' + time.strftime('%Y%m%d-%H%M%S') + '.json')
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['contains_expected_city']:
        raise SystemExit('Smoke test did not return the expected city; inspect saved answer.')
