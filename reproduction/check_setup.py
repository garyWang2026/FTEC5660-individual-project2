"""Read-only offline preflight by default; --embedding and --api are explicit actions."""
import argparse, json, sys, hashlib, importlib, platform
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
p = argparse.ArgumentParser()
p.add_argument('--embedding', action='store_true', help='Download/load the configured local embedding model')
p.add_argument('--api', action='store_true', help='Send ONE short paid API request')
args = p.parse_args()
status = {'python': platform.python_version(), 'architecture': platform.machine()}
for name in ['openai', 'torch', 'sentence_transformers', 'lancedb', 'pyarrow', 'tantivy', 'rouge_score', 'bert_score', 'nltk']:
    importlib.import_module(name)
status['dependencies'] = 'ok'
from main import SimpleMemSystem
status['text_pipeline_import'] = 'ok'
data = ROOT / 'test_ref/locomo10.json'
samples = json.loads(data.read_text())
status['dataset_conversations'] = len(samples)
status['dataset_questions'] = sum(len(s['qa']) for s in samples)
status['dataset_sha256'] = hashlib.sha256(data.read_bytes()).hexdigest()
status['api_key_configured'] = bool(config.OPENAI_API_KEY)
status['provider'] = config.OPENAI_BASE_URL
status['model'] = config.LLM_MODEL
if args.embedding:
    from simplemem.core.utils.embedding import EmbeddingModel
    m = EmbeddingModel()
    v = m.encode_documents(['Alice likes coffee.'])
    assert v.shape == (1, 1024), v.shape
    assert __import__('numpy').isfinite(v).all()
    status['embedding_shape'] = list(v.shape)
if args.api:
    if not config.OPENAI_API_KEY:
        raise SystemExit('请先双击项目中的“配置模型密钥.command”。')
    from openai import OpenAI
    c = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL, max_retries=0, timeout=60)
    try:
        r = c.chat.completions.create(model=config.LLM_MODEL, messages=[{'role':'user','content':'Reply with exactly OK.'}], max_tokens=16, extra_body={'thinking': {'type': 'disabled'}})
    except Exception as exc:
        raise SystemExit('API check failed: ' + type(exc).__name__) from None
    if not r.choices or not r.choices[0].message.content:
        raise SystemExit('API returned no text.')
    status['api_response'] = r.choices[0].message.content
    status['api_usage'] = r.usage.model_dump() if r.usage else None
print(json.dumps(status, ensure_ascii=False, indent=2))
