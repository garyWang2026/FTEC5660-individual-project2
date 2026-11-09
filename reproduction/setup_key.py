"""Local interactive credential entry. No network or third-party dependencies."""
from pathlib import Path
from getpass import getpass
import json
root = Path(__file__).resolve().parents[1]
key = getpass('粘贴 DeepSeek API 密钥，然后按回车（输入不会显示）: ').strip()
if not key or any(c.isspace() for c in key):
    raise SystemExit('未保存：密钥为空或包含空白，请重新运行。')
path = root / '.env'
path.touch(mode=0o600, exist_ok=True)
path.chmod(0o600)
lines = [line for line in path.read_text().splitlines() if not line.startswith('OPENAI_API_KEY=')]
lines.append('OPENAI_API_KEY=' + json.dumps(key))
path.write_text('\n'.join(lines) + '\n')
print('密钥已保存到本机。没有进行模型调用，无需把密钥发到聊天里。')
