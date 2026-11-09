"""Restore the exact public-benchmark memory snapshot without any LLM/API calls."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reproduction/results/formal-20261109'
TARGET=ROOT/'test_results/pilot-20261109T035817Z'


def main():
    protocol=json.loads((ROOT/'reproduction/formal_protocol.json').read_text())
    manifest=json.loads((SOURCE/'snapshot_manifest.jsonl').read_text())
    archive=SOURCE/'memory_db_snapshot.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['archive_sha256']:
        raise SystemExit('Snapshot archive checksum mismatch.')
    entries=[json.loads(line) for line in (SOURCE/'fixed_memories.jsonl').read_text().splitlines()]
    memories=json.dumps(entries,indent=2)
    if hashlib.sha256(memories.encode()).hexdigest()!=protocol['memory_sha256']:
        raise SystemExit('Memory content checksum mismatch.')
    if TARGET.exists():
        if not (TARGET/'memories.json').exists() or (TARGET/'memories.json').read_text()!=memories:
            raise SystemExit('Existing target is different; refusing to overwrite.')
        if not (TARGET/'memory_db').exists():
            raise SystemExit('Existing target lacks database; inspect before restoring.')
        print('Original memory snapshot is already present; no changes made.')
        return
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            path=Path(item.filename)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!='memory_db':
                raise SystemExit('Unexpected archive path.')
        if sum(item.file_size for item in z.infolist())>100*1024**2:
            raise SystemExit('Unexpected archive size.')
        TARGET.mkdir(parents=True,exist_ok=False)
        z.extractall(TARGET)
    (TARGET/'memories.json').write_text(memories)
    pilot=json.loads((ROOT/'reproduction/results/pilot-20261109/summary.jsonl').read_text())
    (TARGET/'summary.json').write_text(json.dumps(pilot,indent=2)+'\n')
    print('Exact fixed benchmark memory restored; no API calls were made.')


if __name__=='__main__':main()
