"""Independent new-conversation replication, reusing the frozen formal query runner."""
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
import argparse,hashlib,json,random,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reproduction.formal_budget import BudgetLedger,ExperimentStop
from reproduction.run_pilot import convert_dialogues

PLAN=ROOT/'reproduction/replication_plan.json'
PROTOCOL=ROOT/'reproduction/replication_protocol.json'
RUN=ROOT/'test_results/replication-20261109-conv49'
SOURCE=ROOT/'test_results/replication-memory-20261109-conv49'


def make_plan():
    path=ROOT/'test_ref/locomo10.json';data=json.loads(path.read_text())
    candidates=[]
    for i,s in enumerate(data):
        if i==0:continue
        counts={c:sum(q['category']==c and q.get('answer') is not None for q in s['qa']) for c in [1,2,3,4]}
        if min(counts.values())<10:continue
        turns=[turn for key,session in s['conversation'].items() if key.startswith('session_') and isinstance(session,list) for turn in session]
        characters=sum(len(t.get('text',''))+len(t.get('blip_caption','')) for t in turns)
        candidates.append((characters,i,len(turns)))
    characters,index,turns=min(candidates)
    sample=data[index]
    rng=random.Random(5662);chosen=[]
    for c in [1,2,3,4]:
        pool=[i for i,q in enumerate(sample['qa']) if q['category']==c and q.get('answer') is not None]
        chosen+=rng.sample(pool,10)
    chosen.sort()
    return {'version':1,'purpose':'new-conversation replication, not retuning the original experiment','sample_index':index,'sample_id':sample['sample_id'],'dialogue_turns':turns,'characters':characters,'selection_rule':'Among non-pilot conversations with at least 10 answered questions in every category 1–4, choose the least dialogue+caption characters to fit the fixed budget. No outcome-based selection.','data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'selection_seed':5662,'question_indices':chosen,'questions':[{'qa_index':i,**sample['qa'][i]} for i in chosen],'conditions':['reflection_on','reflection_off'],'trials':3,'new_question_runs':240,'new_unique_questions':40,'combined_unique_questions':80,'combined_conversations':2,'combined_question_runs':480,'additional_budget_cny':4.5,'user_authorized_additional_cny':5.0,'model':'deepseek-flash','memory_build_output_cap':8192,'question_output_cap':4096,'same_query_settings_as_original':True,'price_source':'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/','price_checked_on':'2026-11-09'}


def build_memory():
    plan=json.loads(PLAN.read_text())
    if plan!=make_plan():raise SystemExit('Frozen replication plan does not match dataset/selection.')
    if SOURCE.exists() and (SOURCE/'memories.json').exists():
        print('Completed memory already present; skipping all construction calls.')
        return
    if SOURCE.exists() and (SOURCE/'memory_db').exists():
        raise SystemExit('Partial memory database found; inspect before spending more.')
    import config,torch
    if config.LLM_MODEL!='deepseek-flash' or config.OPENAI_BASE_URL.rstrip('/')!='https://api.deepseek.com':raise SystemExit('Unexpected model/provider for price accounting.')
    torch.set_num_threads(4)
    from main import SimpleMemSystem
    RUN.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
    ledger=BudgetLedger(RUN/'api_ledger.jsonl',plan['additional_budget_cny'])
    console=sys.stdout
    with (RUN/'build_engine.log').open('a',buffering=1) as log,redirect_stdout(log),redirect_stderr(log):
        system=SimpleMemSystem(db_path=str(SOURCE/'memory_db'),clear_db=False,enable_parallel_processing=True,max_parallel_workers=2,enable_parallel_retrieval=False,use_streaming=False,enable_thinking=False)
        system.llm_client.client=system.llm_client.client.with_options(timeout=120,max_retries=0)
        system.llm_client.client.chat.completions.create=ledger.wrap(system.llm_client.client.chat.completions.create,output_cap=8192,default_key='build:'+plan['sample_id'],default_stage='build_memory')
        worker=system.memory_builder._generate_memory_entries_worker
        def checked_worker(*args,**kwargs):
            result=worker(*args,**kwargs)
            if not result:raise ExperimentStop('A dialogue window produced no entries; inspect before evaluation.')
            return result
        system.memory_builder._generate_memory_entries_worker=checked_worker
        sample=json.loads((ROOT/'test_ref/locomo10.json').read_text())[plan['sample_index']]
        start=time.perf_counter();completed=False
        try:
            dialogues=convert_dialogues(sample)
            assert len(dialogues)==plan['dialogue_turns']
            system.add_dialogues(dialogues);system.finalize()
            memories=system.get_all_memories()
            if not memories or ledger.summary()['failed_or_unknown_api_calls']:
                raise ExperimentStop('Construction produced no memory or API failures; stop for inspection.')
            (SOURCE/'memories.json').write_text(json.dumps([m.model_dump() for m in memories],indent=2))
            completed=True
        finally:
            result={'completed':completed,'sample_id':plan['sample_id'],'elapsed_seconds':time.perf_counter()-start,'usage':ledger.summary(),'memory_count':len(system.get_all_memories()),'finished_utc':datetime.now(timezone.utc).isoformat()}
            (SOURCE/'build_summary.json').write_text(json.dumps(result,indent=2))
            system.llm_client.client.close()
            print('REPLICATION BUILD SUMMARY '+json.dumps(result),file=console,flush=True)


def make_query_protocol():
    plan=json.loads(PLAN.read_text())
    if plan!=make_plan():raise SystemExit('Data/selection changed.')
    build=json.loads((SOURCE/'build_summary.json').read_text())
    if not build['completed']:raise SystemExit('Memory construction is incomplete.')
    p=json.loads((ROOT/'reproduction/formal_protocol.json').read_text())
    p.update({'sample_index':plan['sample_index'],'sample_id':plan['sample_id'],'data_sha256':plan['data_sha256'],'memory_sha256':hashlib.sha256((SOURCE/'memories.json').read_bytes()).hexdigest(),'memory_source':str(SOURCE.relative_to(ROOT)),'memory_entries':build['memory_count'],'selection_seed':plan['selection_seed'],'excluded_pilot_indices':[],'question_indices':plan['question_indices'],'questions':plan['questions'],'schedule_seed':5663,'formal_budget_upper_cny':plan['additional_budget_cny'],'prior_work_reserve_cny':0,'total_budget_cny':plan['additional_budget_cny'],'additional_experiment_only':True,'memory_build_charged_to_same_ledger':True})
    p['warmup_query']=json.loads((ROOT/'test_ref/locomo10.json').read_text())[plan['sample_index']]['conversation']['speaker_a']
    return p


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--build-memory',action='store_true')
    parser.add_argument('--freeze-query-protocol',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        if PLAN.exists():raise SystemExit('Plan exists; refusing overwrite.')
        p=make_plan();PLAN.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({k:p[k] for k in ['sample_index','sample_id','dialogue_turns','new_unique_questions','new_question_runs','additional_budget_cny']},indent=2));return
    if args.build_memory:build_memory();return
    if args.freeze_query_protocol:
        if PROTOCOL.exists():raise SystemExit('Query protocol already exists.')
        PROTOCOL.write_text(json.dumps(make_query_protocol(),indent=2)+'\n');print('Query protocol fixed; no query API calls made.');return
    from reproduction import run_formal as original
    original.PROTOCOL_PATH=PROTOCOL
    original.RUN=RUN
    original.make_protocol=make_query_protocol
    original.main()


if __name__=='__main__':main()
