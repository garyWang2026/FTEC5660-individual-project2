"""Download the exact ModelScope files pinned in provenance.json; no API key required."""
from pathlib import Path
import concurrent.futures, hashlib, json, subprocess
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
meta=json.loads((ROOT/'reproduction/provenance.json').read_text())
if 'embedding' not in meta:
    raise SystemExit('Model manifest is not yet ready.')
folder=ROOT/'.cache/models/Qwen3-Embedding-0.6B'
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''): h.update(b)
    return h.hexdigest()
def get(e):
    rel=Path(e['path'])
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Invalid model path')
    p=folder/rel
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and digest(p)==e['sha256']:
        return
    tmp=p.with_name(p.name+'.download')
    url='https://modelscope.cn/models/Qwen/Qwen3-Embedding-0.6B/resolve/'+quote(e['revision'])+'/'+quote(e['path'])
    subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','2','--connect-timeout','15','--max-time','1800',url,'--output',str(tmp)],check=True)
    if digest(tmp)!=e['sha256']:
        raise ValueError('Model checksum mismatch: '+e['path'])
    tmp.replace(p)
    print('Verified',e['path'],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(get,meta['embedding']['files']))
print('All model files verified.')
