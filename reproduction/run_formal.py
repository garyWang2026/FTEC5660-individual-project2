"""Fixed 40-question, 3-trial reflection ablation; resumption shares one persistent budget."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reproduction.formal_budget import BudgetLedger, ExperimentStop
from reproduction.formal_metrics import locomo_f1
from reproduction.run_pilot import upstream_f1

PROTOCOL_PATH = ROOT/'reproduction/formal_protocol.json'
RUN = ROOT/'test_results/formal-20261109'


def make_protocol():
    data_path=ROOT/'test_ref/locomo10.json'
    sample=json.loads(data_path.read_text())[0]
    pilot=ROOT/'test_results/pilot-20261109T035817Z'
    pilot_summary=json.loads((pilot/'summary.json').read_text())
    excluded=set(pilot_summary['metadata']['question_indices'])
    rng=random.Random(5660)
    indices=[]
    for category in [1,2,3,4]:
        pool=[i for i,q in enumerate(sample['qa']) if q['category']==category and q.get('answer') is not None and i not in excluded]
        indices.extend(rng.sample(pool,10))
    indices.sort()
    memory_sha=hashlib.sha256((pilot/'memories.json').read_bytes()).hexdigest()
    return {'version':1,'sample_id':sample['sample_id'],'sample_index':0,'data_sha256':hashlib.sha256(data_path.read_bytes()).hexdigest(),'memory_sha256':memory_sha,'memory_source':'test_results/pilot-20261109T035817Z','memory_entries':454,'selection_seed':5660,'excluded_pilot_indices':sorted(excluded),'question_indices':indices,'questions':[{'qa_index':i,**sample['qa'][i]} for i in indices],'conditions':['reflection_on','reflection_off'],'trials':3,'model':'deepseek-flash','thinking':False,'streaming':False,'planning':True,'max_reflection_rounds':2,'query_workers_per_condition':1,'paired_question_concurrency':2,'embedding_device':'cpu','cpu_threads':4,'memory_fixed_across_all_trials':True,'upstream_prompts_unchanged':True,'model_seed':None,'schedule_seed':5661,'primary_metric':'category-aware official LoCoMo F1','secondary_metric':'SimpleMem upstream set-token F1','scorer_source':'https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py','formal_budget_upper_cny':9.0,'prior_work_reserve_cny':1.0,'total_budget_cny':10.0,'price_source':'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/','price_checked_on':'2026-11-09','price_peak_cny_per_million':{'input_miss':2,'input_hit':.04,'output':8},'budget_reserves_unknown_usage_at_full_bound':True,'output_cap':4096,'sdk_retries':0,'request_timeout_seconds':90,'latency_note':'Two arms run concurrently on each question; elapsed latency is under this fixed paired workload, not isolated single-request latency. No inference about across-conversation or memory-build variance.'}


def memory_digest(entries):
    return hashlib.sha256(json.dumps(sorted((m.model_dump() for m in entries),key=lambda m:m['entry_id']),sort_keys=True).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        if PROTOCOL_PATH.exists():
            raise SystemExit('Protocol already frozen; refusing to overwrite.')
        protocol=make_protocol()
        PROTOCOL_PATH.write_text(json.dumps(protocol,indent=2)+'\n')
        print('Frozen protocol:',len(protocol['question_indices']),'questions; 3 trials × 2 conditions; overall 10 CNY ceiling.')
        return
    protocol=json.loads(PROTOCOL_PATH.read_text())
    if protocol!=make_protocol():
        raise SystemExit('Protocol/data/memory no longer matches the frozen selection.')
    import config
    if config.LLM_MODEL!='deepseek-flash' or config.OPENAI_BASE_URL.rstrip('/')!='https://api.deepseek.com' or config.ENABLE_THINKING:
        raise SystemExit('Model/provider/thinking differs from frozen protocol.')
    RUN.mkdir(parents=True,exist_ok=True)
    protocol_sha=hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    snapshot=RUN/'protocol.json'
    if snapshot.exists() and hashlib.sha256(snapshot.read_bytes()).hexdigest()!=protocol_sha:
        raise SystemExit('Cannot resume a different protocol in the same run directory.')
    if not snapshot.exists():shutil.copy2(PROTOCOL_PATH,snapshot)
    if not (RUN/'memory_db').exists():shutil.copytree(ROOT/protocol['memory_source']/'memory_db',RUN/'memory_db')
    ledger=BudgetLedger(RUN/'api_ledger.jsonl',protocol['formal_budget_upper_cny'])
    rows_path=RUN/'questions.jsonl'
    rows=[json.loads(l) for l in rows_path.read_text().splitlines()] if rows_path.exists() else []
    done={r['key'] for r in rows}
    if len(done)!=len(rows):raise SystemExit('Duplicate result keys; inspect before continuing.')
    console=sys.stdout
    row_lock=threading.Lock()
    completed=False
    stop_reason=None
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    runtime=RUN/'runtime.json'
    if not runtime.exists():runtime.write_text(json.dumps({'started_utc':datetime.now(timezone.utc).isoformat(),'git_commit':git_commit,'protocol_sha256':protocol_sha},indent=2))
    with (RUN/'engine.log').open('a',buffering=1) as engine,redirect_stdout(engine),redirect_stderr(engine):
        import torch
        torch.set_num_threads(protocol['cpu_threads'])
        from simplemem.core.utils.embedding import EmbeddingModel
        from simplemem.core.database.vector_store import VectorStore
        from simplemem.core.utils.llm_client import LLMClient
        from simplemem.core.hybrid_retriever import HybridRetriever
        from simplemem.core.answer_generator import AnswerGenerator
        embedder=EmbeddingModel()
        original_encode=embedder.encode_single
        embedding_lock=threading.Lock()
        def locked_encode(*args,**kwargs):
            with embedding_lock:return original_encode(*args,**kwargs)
        embedder.encode_single=locked_encode
        store=VectorStore(db_path=str(RUN/'memory_db'),embedding_model=embedder)
        before_hash=memory_digest(store.get_all_entries())
        source_memories=json.loads((ROOT/protocol['memory_source']/'memories.json').read_text())
        assert len(store.get_all_entries())==protocol['memory_entries']
        assert before_hash==hashlib.sha256(json.dumps(sorted(source_memories,key=lambda m:m['entry_id']),sort_keys=True).encode()).hexdigest()
        # Warm both identical read-only search routes before timed trials; no API calls.
        assert store.semantic_search(protocol.get('warmup_query','Caroline'),top_k=1)
        assert store.keyword_search([protocol.get('warmup_query','Caroline')],top_k=1)
        pipelines={}
        for condition in protocol['conditions']:
            llm=LLMClient(use_streaming=False,enable_thinking=False)
            llm.client=llm.client.with_options(timeout=90,max_retries=0)
            llm.client.chat.completions.create=ledger.wrap(llm.client.chat.completions.create)
            retriever=HybridRetriever(llm,store,enable_planning=True,enable_reflection=condition=='reflection_on',max_reflection_rounds=2,enable_parallel_retrieval=False)
            pipelines[condition]=(llm,retriever,AnswerGenerator(llm))

        def work(trial,condition,qa):
            key=f'{trial}:{condition}:{qa["qa_index"]}'
            if key in done:return
            llm,retriever,generator=pipelines[condition]
            ledger.set_context(key,'retrieval')
            t=time.perf_counter(); contexts=retriever.retrieve(qa['question']); retrieval=time.perf_counter()-t
            ledger.set_context(key,'answer')
            t=time.perf_counter(); answer=generator.generate_answer(qa['question'],contexts); answer_time=time.perf_counter()-t
            usage=ledger.summary(key)
            failed=usage['failed_or_unknown_api_calls']>0 or answer in ['Failed to generate answer','No relevant information found']
            row={'key':key,'trial':trial,'condition':condition,'qa_index':qa['qa_index'],'category':qa['category'],'question':qa['question'],'reference':str(qa['answer']),'answer':answer,'failed':failed,'locomo_f1':0 if failed else locomo_f1(answer,qa['answer'],qa['category']),'upstream_f1':0 if failed else upstream_f1(answer,qa['answer']),'retrieval_seconds':retrieval,'answer_seconds':answer_time,'total_seconds':retrieval+answer_time,'retrieved_memories':len(contexts),'retrieved_ids':[m.entry_id for m in contexts],'usage':usage,'completed_utc':datetime.now(timezone.utc).isoformat()}
            with row_lock:
                with rows_path.open('a') as f:
                    f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
                rows.append(row);done.add(key)
                print(f'FORMAL {len(rows)}/240 | trial {trial} | {condition} | q{qa["qa_index"]} | F1 {row["locomo_f1"]:.3f} | reserved/charged upper CNY {ledger.committed():.3f}',file=console,flush=True)

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                for trial in range(1,4):
                    order=list(protocol['questions']);rng=random.Random(protocol['schedule_seed']+trial);rng.shuffle(order)
                    for qa in order:
                        conditions=list(protocol['conditions']);rng.shuffle(conditions)
                        futures=[pool.submit(work,trial,c,qa) for c in conditions if f'{trial}:{c}:{qa["qa_index"]}' not in done]
                        for future in futures:future.result()
            completed=len(rows)==240
        except ExperimentStop as exc:
            stop_reason=str(exc)
        finally:
            assert memory_digest(store.get_all_entries())==before_hash,'Memory changed during experiment.'
            for llm,_,_ in pipelines.values():llm.client.close()
            summary={'completed':completed,'completed_question_runs':len(rows),'planned_question_runs':240,'stop_reason':stop_reason,'usage':ledger.summary(),'memory_unchanged':True,'protocol_sha256':protocol_sha}
            (RUN/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
            print('FORMAL SUMMARY '+json.dumps(summary),file=console,flush=True)
    if not completed:raise SystemExit(2)


if __name__=='__main__':main()
