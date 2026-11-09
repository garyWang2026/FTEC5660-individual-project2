"""Offline cross-conversation analysis; retains original and replication results separately."""
from collections import Counter
import csv,json,shutil,statistics,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from reproduction.formal_budget import BudgetLedger

RUN=ROOT/'test_results/replication-20261109-conv49'
SOURCE=ROOT/'test_results/replication-memory-20261109-conv49'
OUT=ROOT/'reproduction/results/replication-20261109'
CONDITIONS=['reflection_on','reflection_off']


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def group_stats(rows):
    result={}
    for c in CONDITIONS:
        trials=[]
        for t in range(1,4):
            a=[r for r in rows if r['condition']==c and r['trial']==t]
            trials.append({'f1':statistics.mean(r['locomo_f1'] for r in a),'upstream_f1':statistics.mean(r['upstream_f1'] for r in a),'tokens':statistics.mean(r['usage']['total_tokens'] for r in a),'latency':statistics.mean(r['total_seconds'] for r in a),'calls':statistics.mean(r['usage']['api_calls'] for r in a)})
        result[c]={k:{'mean':statistics.mean(r[k] for r in trials),'sd':statistics.stdev(r[k] for r in trials)} for k in trials[0]}
    on,off=result['reflection_on'],result['reflection_off']
    result['comparison']={'f1_off_minus_on_points':100*(off['f1']['mean']-on['f1']['mean']),'token_saving_percent':100*(1-off['tokens']['mean']/on['tokens']['mean']),'latency_saving_percent':100*(1-off['latency']['mean']/on['latency']['mean']),'call_saving_percent':100*(1-off['calls']['mean']/on['calls']['mean'])}
    return result


def main():
    archived='--archived' in sys.argv
    source=OUT if archived else RUN
    metadata=json.loads((OUT/'run_metadata.jsonl').read_text()) if archived else None
    state=metadata['summary'] if archived else json.loads((RUN/'summary.json').read_text())
    if not state['completed']:raise SystemExit('Replication incomplete; preserve partial results without claiming completion.')
    plan=json.loads((ROOT/'reproduction/replication_plan.json').read_text())
    protocol=json.loads((ROOT/'reproduction/replication_protocol.json').read_text())
    new=[json.loads(l) for l in (source/'questions.jsonl').read_text().splitlines()]
    old=[json.loads(l) for l in (ROOT/'reproduction/results/formal-20261109/questions.jsonl').read_text().splitlines()]
    expected={(t,c,i) for t in range(1,4) for c in CONDITIONS for i in plan['question_indices']}
    assert len(new)==240 and {(r['trial'],r['condition'],r['qa_index']) for r in new}==expected
    assert Counter((r['trial'],r['condition'],r['category']) for r in new)==Counter({(t,c,k):10 for t in range(1,4) for c in CONDITIONS for k in range(1,5)})
    ledger=BudgetLedger(source/'api_ledger.jsonl',4.5)
    total=ledger.summary()
    query_events={i:e for i,e in ledger.events.items() if e['stage']!='build_memory'}
    memory_events={i:e for i,e in ledger.events.items() if e['stage']=='build_memory'}
    assert sum(r['usage']['api_calls'] for r in new)==len(query_events)
    assert sum(r['usage']['total_tokens'] for r in new)==sum(e.get('total_tokens',0) for e in query_events.values())
    assert total['charged_upper_cny']<=4.5 and state['memory_unchanged']
    OUT.mkdir(parents=True,exist_ok=True)
    if not archived:
        for name in ['questions.jsonl','api_ledger.jsonl']:shutil.copy2(RUN/name,OUT/name)
        (OUT/'run_metadata.jsonl').write_text(json.dumps({'runtime':json.loads((RUN/'runtime.json').read_text()),'summary':state,'protocol':protocol,'plan':plan})+'\n')
        build=json.loads((SOURCE/'build_summary.json').read_text())
        (OUT/'build_summary.jsonl').write_text(json.dumps(build)+'\n')
    combined=[dict(r,sample_id=sid) for sid,group in [('conv-26',old),('conv-49',new)] for r in group]
    write_csv(OUT/'questions.csv',[{k:r[k] for k in ['sample_id','trial','condition','qa_index','category','question','reference','answer','locomo_f1','upstream_f1','total_seconds','failed']}|r['usage'] for r in combined])
    stats={'conv-26':group_stats(old),'conv-49':group_stats(new),'combined':group_stats(combined)}
    table=[]
    for sid in stats:
        for c in CONDITIONS:
            row={'sample_id':sid,'condition':c}
            for k,v in stats[sid][c].items():row[k+'_mean']=v['mean'];row[k+'_sd']=v['sd']
            table.append(row)
    write_csv(OUT/'condition_summary.csv',table)
    differences=[]
    for sid in ['conv-26','conv-49']:
        for i in sorted({r['qa_index'] for r in combined if r['sample_id']==sid}):
            values={c:statistics.mean(r['locomo_f1'] for r in combined if r['sample_id']==sid and r['qa_index']==i and r['condition']==c) for c in CONDITIONS}
            differences.append(values['reflection_off']-values['reflection_on'])
    rng=np.random.default_rng(5664)
    interval=np.quantile(rng.choice(differences,size=(10000,80),replace=True).mean(axis=1),[.025,.975])*100
    results={'stats':stats,'new_total_usage':total,'new_build_api_calls':len(memory_events),'new_query_api_calls':len(query_events),'combined_conditional_bootstrap_ci_points':interval.tolist(),'new_question_runs':len(new),'combined_question_runs':len(combined),'combined_unique_questions':80,'conversations':2}
    (OUT/'analysis.jsonl').write_text(json.dumps(results)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(11.5,4))
    for ax,(metric,scale,label) in zip(axes,[('f1',100,'LoCoMo F1 (points)'),('tokens',.001,'API tokens per question (thousands)'),('latency',1,'Question latency (seconds)')]):
        v=[stats['combined'][c][metric]['mean']*scale for c in CONDITIONS];e=[stats['combined'][c][metric]['sd']*scale for c in CONDITIONS]
        ax.bar([0,1],v,yerr=e,capsize=4,color=['#254E70','#D17A22'],width=.62)
        ax.set_xticks([0,1],['Reflection\non','Reflection\noff']);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.set_ylim(0,max(a+b for a,b in zip(v,e))*1.22)
        for x,a,b in zip([0,1],v,e):ax.text(x,a+b+max(v)*.025,f'{a:.2f}',ha='center')
    fig.suptitle('SimpleMem: replication across two LoCoMo conversations',fontsize=14,fontweight='bold')
    fig.text(.5,.01,'80 questions | 2 conversations | 3 trials per condition | fixed per-conversation memory | error bars: trial SD',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,.92]);fig.savefig(OUT/'comparison.png',dpi=200);fig.savefig(OUT/'comparison.svg');plt.close(fig)
    p=OUT/'comparison.svg';p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
    report='''# Independent conversation replication and combined results

The original result is retained separately. An additional complete long conversation was evaluated with the same settings, then both results were combined.

## Scope

- conv-26: 419 turns, 40 questions, two arms x three trials = 240 question-runs.
- conv-49: 509 turns, 40 questions, two arms x three trials = 240 additional runs.
- Total: two conversations, 80 distinct questions, 480 runs. Each conversation has ten questions per category 1-4.
- The extension selected the shortest unused eligible conversation by dialogue-plus-caption characters, requiring at least ten answered questions per category. This cost rule and question selection were fixed before new answer scores existed.
- DeepSeek Flash; thinking off; planning on; two concurrent arms; four CPU threads; 4096 output tokens/request. Only reflection differs between arms.

## Results by conversation and combined

| Scope | Reflection on F1 | Reflection off F1 | Off minus on, points | Token reduction | Latency reduction |
|---|---:|---:|---:|---:|---:|
'''
    labels={'conv-26':'Original: conv-26','conv-49':'Extension: conv-49','combined':'Combined'}
    for sid in stats:
        g=stats[sid];d=g['comparison']
        report+=f"| {labels[sid]} | {g['reflection_on']['f1']['mean']*100:.2f} | {g['reflection_off']['f1']['mean']*100:.2f} | {d['f1_off_minus_on_points']:+.2f} | {d['token_saving_percent']:.1f}% | {d['latency_saving_percent']:.1f}% |\n"
    report+='\nScores are means across three trial aggregates, not correctness rates. Equal question counts give both conversations equal weight.\n\n![Combined quality, token usage and latency](comparison.png)\n'
    g=stats['combined']
    report+=f'''
## Combined variability and limits

Category-aware LoCoMo F1, mean +/- trial sample SD: reflection on {g['reflection_on']['f1']['mean']*100:.2f} +/- {g['reflection_on']['f1']['sd']*100:.2f}; reflection off {g['reflection_off']['f1']['mean']*100:.2f} +/- {g['reflection_off']['f1']['sd']*100:.2f}.
After averaging trials per question, 10,000 paired question bootstrap samples give [{interval[0]:+.2f}, {interval[1]:+.2f}] F1 points for off minus on, conditional on these two fixed conversations and memories. This is not a population interval or non-inferiority proof. The cost-selected extension and once-built memories limit generalization.
Timing is measured with both arms running concurrently; runtime periods may also affect absolute cross-conversation latency. Lexical F1 is not semantic correctness; original set-token F1 and all raw answers are retained.

## Extension usage and checks

Construction plus queries: {total['api_calls']} API calls, {total['total_tokens']:,} tokens; {len(memory_events)} build calls and {len(query_events)} query calls.
Estimated price-list cost: CNY {total['estimated_off_peak_cny']:.4f}-{total['charged_upper_cny']:.4f}, including build and queries under the same CNY 4.5 extension cap. Prior experiments are outside this cap. This is not an invoice; unknown reservations are CNY {total['unknown_reservations']:.4f}.
Failed/unknown API calls: {total['failed_or_unknown_api_calls']}; failed questions: {sum(r['failed'] for r in new)}. All 240 extension tuples are complete, per-question usage matches the ledger, and memory content/IDs are unchanged.

## Files and references

- `condition_summary.csv`: per-conversation and combined means/sample SDs.
- `questions.csv`: all 480 original and extension answers, references, scores and usage.
- `questions.jsonl` / `api_ledger.jsonl`: raw extension answers and persistent cost ledger.
- `run_metadata.jsonl` / `build_summary.jsonl`: fixed settings and build provenance.
- [Original result](../formal-20261109/RESULTS.md), [LoCoMo](https://github.com/snap-research/locomo), [official pricing](https://api-docs.deepseek.com/quick_start/pricing/).
'''
    notes=OUT/'DISCUSSION.md'
    if notes.exists():report+='\n'+notes.read_text()
    (OUT/'RESULTS.md').write_text(report)
    print(json.dumps(results,indent=2));print('Report:',OUT/'RESULTS.md')


if __name__=='__main__':main()
