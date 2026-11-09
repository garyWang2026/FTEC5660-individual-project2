"""Download the pinned official dataset and verify its SHA-256."""
from pathlib import Path
import json, hashlib, subprocess
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'reproduction/provenance.json').read_text())['dataset']
url='https://raw.githubusercontent.com/snap-research/locomo/'+source['commit']+'/'+source['path']
dest=ROOT/'test_ref/locomo10.json'
temp=dest.with_suffix('.download')
subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','120',url,'--output',str(temp)],check=True)
if hashlib.sha256(temp.read_bytes()).hexdigest()!=source['sha256']:
    raise SystemExit('Dataset checksum mismatch: file not installed.')
temp.replace(dest)
print('Official dataset downloaded and verified.')
