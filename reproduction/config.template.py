"""Local runtime configuration; credentials are read from .env, never printed."""
import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
os.environ.setdefault('HF_HOME', str(ROOT / '.cache' / 'huggingface'))
os.environ.setdefault('REQUESTS_CA_BUNDLE', '/etc/ssl/cert.pem')
os.environ.setdefault('SSL_CERT_FILE', '/etc/ssl/cert.pem')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-flash')
LOCAL_EMBEDDING = ROOT / '.cache/models/Qwen3-Embedding-0.6B'
EMBEDDING_MODEL = str(LOCAL_EMBEDDING) if (LOCAL_EMBEDDING / 'model.safetensors').exists() else 'Qwen/Qwen3-Embedding-0.6B'
# CPU avoids a Metal/MPS shape-inference crash on this Mac with torch 2.6.0.
EMBEDDING_DEVICE = 'cpu'
ENABLE_THINKING = False
USE_STREAMING = False
USE_JSON_FORMAT = False
ENABLE_PLANNING = True
ENABLE_REFLECTION = True
MAX_REFLECTION_ROUNDS = 2
ENABLE_PARALLEL_PROCESSING = True
MAX_PARALLEL_WORKERS = 2
ENABLE_PARALLEL_RETRIEVAL = True
MAX_RETRIEVAL_WORKERS = 2
LANCEDB_PATH = str(ROOT / 'lancedb_data')
