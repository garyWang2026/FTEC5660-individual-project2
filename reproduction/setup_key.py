"""Local interactive credential entry. No network or third-party dependencies."""
from pathlib import Path
from getpass import getpass
import json
root = Path(__file__).resolve().parents[1]
key = getpass('Paste your DeepSeek API key and press Enter (input is hidden): ').strip()
if not key or any(c.isspace() for c in key):
    raise SystemExit('Not saved: the key is empty or contains whitespace. Run this tool again.')
path = root / '.env'
path.touch(mode=0o600, exist_ok=True)
path.chmod(0o600)
lines = [line for line in path.read_text().splitlines() if not line.startswith('OPENAI_API_KEY=')]
lines.append('OPENAI_API_KEY=' + json.dumps(key))
path.write_text('\n'.join(lines) + '\n')
print('Key saved locally. No model request was sent. Do not share your key in chat.')
