"""Restore the public conv-49 memory snapshot without paid model construction."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reproduction/results/replication-20261109'
TARGET=ROOT/'test_results/replication-memory-20261109-conv49'


def main():
    protocol=json.loads((ROOT/'reproduction/replication_protocol.json').read_text())
    manifest=json.loads((SOURCE/'snapshot_manifest.jsonl').read_text())
    archive=SOURCE/'memory_db_snapshot.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['archive_sha256']:raise SystemExit('Archive checksum mismatch.')
    entries=[json.loads(line) for line in (SOURCE/'fixed_memories.jsonl').read_text().splitlines()]
    memories=json.dumps(entries,indent=2)
    if hashlib.sha256(memories.encode()).hexdigest()!=protocol['memory_sha256']:raise SystemExit('Memory checksum mismatch.')
    if TARGET.exists():
        if not (TARGET/'memories.json').exists() or (TARGET/'memories.json').read_text()!=memories or not (TARGET/'memory_db').exists():
            raise SystemExit('Existing memory directory is different/incomplete; refusing overwrite.')
        print('Replication memory already present; no changes made.');return
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='memory_db':raise SystemExit('Unexpected archive path.')
        if sum(item.file_size for item in z.infolist())>100*1024**2:raise SystemExit('Unexpected archive size.')
        TARGET.mkdir(parents=True,exist_ok=False);z.extractall(TARGET)
    (TARGET/'memories.json').write_text(memories)
    summary=json.loads((SOURCE/'build_summary.jsonl').read_text())
    (TARGET/'build_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Exact replication memory restored; no API calls made.')


if __name__=='__main__':main()
