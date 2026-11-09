"""Validate and archive completed formal runs; generate tables and scientific plots offline."""
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import statistics
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reproduction.formal_budget import BudgetLedger

RUN=ROOT/'test_results/formal-20261109'
OUT=ROOT/'reproduction/results/formal-20261109'
CONDITIONS=['reflection_on','reflection_off']
LABELS={'reflection_on':'Reflection on','reflection_off':'Reflection off'}


def mean_sd(values):
    return statistics.mean(values),statistics.stdev(values) if len(values)>1 else 0.0


def csv_file(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def main():
    archived='--archived' in sys.argv
    source=OUT if archived else RUN
    metadata=json.loads((OUT/'run_metadata.jsonl').read_text()) if archived else None
    summary=metadata['summary'] if archived else json.loads((RUN/'summary.json').read_text())
    if not summary['completed']:
        raise SystemExit('Run incomplete; refusing to create a completed-experiment report.')
    protocol=metadata['protocol'] if archived else json.loads((RUN/'protocol.json').read_text())
    rows=[json.loads(l) for l in (source/'questions.jsonl').read_text().splitlines()]
    expected={(t,c,i) for t in range(1,4) for c in CONDITIONS for i in protocol['question_indices']}
    actual={(r['trial'],r['condition'],r['qa_index']) for r in rows}
    assert len(rows)==len(actual)==240 and actual==expected
    assert Counter((r['condition'],r['trial'],r['category']) for r in rows)==Counter({(c,t,k):10 for c in CONDITIONS for t in range(1,4) for k in range(1,5)})
    ledger=BudgetLedger(source/'api_ledger.jsonl',9)
    usage=ledger.summary()
    assert usage['charged_upper_cny']<=9
    assert sum(r['usage']['api_calls'] for r in rows)==usage['api_calls']
    assert sum(r['usage']['total_tokens'] for r in rows)==usage['total_tokens']
    assert summary['memory_unchanged']
    OUT.mkdir(parents=True,exist_ok=True)
    if not archived:
        shutil.copy2(RUN/'questions.jsonl',OUT/'questions.jsonl')
        shutil.copy2(RUN/'api_ledger.jsonl',OUT/'api_ledger.jsonl')
        (OUT/'run_metadata.jsonl').write_text(json.dumps({'runtime':json.loads((RUN/'runtime.json').read_text()),'summary':summary,'protocol':protocol})+'\n')
    flat=[]
    for r in sorted(rows,key=lambda r:(r['trial'],r['qa_index'],r['condition'])):
        flat.append({k:r[k] for k in ['trial','condition','qa_index','category','question','reference','answer','failed','locomo_f1','upstream_f1','retrieval_seconds','answer_seconds','total_seconds','retrieved_memories']} | r['usage'])
    csv_file(OUT/'questions.csv',flat)
    trial_rows=[]
    for condition in CONDITIONS:
        for trial in range(1,4):
            group=[r for r in rows if r['condition']==condition and r['trial']==trial]
            trial_rows.append({'condition':condition,'trial':trial,'questions':len(group),'locomo_f1':statistics.mean(r['locomo_f1'] for r in group),'upstream_f1':statistics.mean(r['upstream_f1'] for r in group),'mean_latency_seconds':statistics.mean(r['total_seconds'] for r in group),'mean_api_calls':statistics.mean(r['usage']['api_calls'] for r in group),'mean_tokens':statistics.mean(r['usage']['total_tokens'] for r in group),'total_tokens':sum(r['usage']['total_tokens'] for r in group),'cost_off_peak_cny':sum(r['usage']['estimated_off_peak_cny'] for r in group),'cost_upper_cny':sum(r['usage']['charged_upper_cny'] for r in group),'failed_questions':sum(r['failed'] for r in group)})
    csv_file(OUT/'trials.csv',trial_rows)
    stats={}
    for c in CONDITIONS:
        trials=[r for r in trial_rows if r['condition']==c]
        stats[c]={m:dict(zip(['mean','sd'],mean_sd([r[m] for r in trials]))) for m in ['locomo_f1','upstream_f1','mean_latency_seconds','mean_api_calls','mean_tokens']}
    categories=[]
    for c in CONDITIONS:
        for category in range(1,5):
            scores=[statistics.mean(r['locomo_f1'] for r in rows if r['condition']==c and r['category']==category and r['trial']==t) for t in range(1,4)]
            avg,sd=mean_sd(scores)
            categories.append({'condition':c,'category':category,'unique_questions':10,'runs':3,'locomo_f1_mean':avg,'locomo_f1_sd':sd})
    csv_file(OUT/'categories.csv',categories)
    paired=[]
    for idx in protocol['question_indices']:
        on=statistics.mean(r['locomo_f1'] for r in rows if r['qa_index']==idx and r['condition']=='reflection_on')
        off=statistics.mean(r['locomo_f1'] for r in rows if r['qa_index']==idx and r['condition']=='reflection_off')
        paired.append({'qa_index':idx,'on_f1':on,'off_f1':off,'off_minus_on':off-on})
    csv_file(OUT/'paired_questions.csv',paired)
    diffs=np.array([r['off_minus_on'] for r in paired])
    rng=np.random.default_rng(5660)
    bootstrap=rng.choice(diffs,size=(10000,len(diffs)),replace=True).mean(axis=1)
    ci=np.quantile(bootstrap,[.025,.975])
    on,off=stats['reflection_on'],stats['reflection_off']
    delta=100*(off['locomo_f1']['mean']-on['locomo_f1']['mean'])
    tokens_saved=100*(1-off['mean_tokens']['mean']/on['mean_tokens']['mean'])
    latency_saved=100*(1-off['mean_latency_seconds']['mean']/on['mean_latency_seconds']['mean'])
    calls_saved=100*(1-off['mean_api_calls']['mean']/on['mean_api_calls']['mean'])
    findings={'stats':stats,'categories':categories,'delta_off_minus_on_f1_points':delta,'conditional_bootstrap_ci_points':(100*ci).tolist(),'tokens_saved_percent':tokens_saved,'latency_saved_percent':latency_saved,'api_calls_saved_percent':calls_saved,'usage':usage,'paired_better':int((diffs>0).sum()),'paired_worse':int((diffs<0).sum()),'paired_tied':int((diffs==0).sum())}
    (OUT/'analysis.jsonl').write_text(json.dumps(findings,indent=None)+'\n')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    colors=['#254E70','#D17A22']
    fig,axes=plt.subplots(1,3,figsize=(11.5,4))
    panels=[('locomo_f1',100,'LoCoMo F1 (points)'),('mean_tokens',1/1000,'API tokens per question (thousands)'),('mean_latency_seconds',1,'Question latency (seconds)')]
    for ax,(metric,scale,label) in zip(axes,panels):
        values=[stats[c][metric]['mean']*scale for c in CONDITIONS]
        errors=[stats[c][metric]['sd']*scale for c in CONDITIONS]
        ax.bar([0,1],values,yerr=errors,color=colors,capsize=4,width=.62)
        ax.set_xticks([0,1],['Reflection\non','Reflection\noff']);ax.set_ylabel(label)
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        for x,v,e in zip([0,1],values,errors):ax.text(x,v+e+max(values)*.025,f'{v:.2f}',ha='center',fontsize=10)
        ax.set_ylim(0,max(v+e for v,e in zip(values,errors))*1.22)
    fig.suptitle('SimpleMem: reflection ablation on a fixed LoCoMo subset',fontsize=14,fontweight='bold')
    fig.text(.5,.01,'40 held-out questions | 3 trials per condition | fixed memory | 2 concurrent arms | error bars: trial SD',ha='center',fontsize=9,color='#444444')
    fig.tight_layout(rect=[0,.05,1,.92]);fig.savefig(OUT/'comparison.png',dpi=200);fig.savefig(OUT/'comparison.svg');plt.close(fig)

    svg=OUT/'comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')

    def fmt(c,m,scale=1):
        return f"{stats[c][m]['mean']*scale:.2f} ± {stats[c][m]['sd']*scale:.2f}"
    report=f'''# SimpleMem: first-conversation reproduction and reflection ablation

Date: 2026-11-09. Completed 40 held-out questions x 2 conditions x 3 trials = 240 question-runs.

## Main results

| Metric (mean +/- sample SD across three trial aggregates) | Reflection on | Reflection off |
|---|---:|---:|
| Category-aware LoCoMo F1, 0-100 | {fmt('reflection_on','locomo_f1',100)} | {fmt('reflection_off','locomo_f1',100)} |
| Original SimpleMem set-token F1, 0-100 | {fmt('reflection_on','upstream_f1',100)} | {fmt('reflection_off','upstream_f1',100)} |
| All API tokens per question | {fmt('reflection_on','mean_tokens')} | {fmt('reflection_off','mean_tokens')} |
| API calls per question | {fmt('reflection_on','mean_api_calls')} | {fmt('reflection_off','mean_api_calls')} |
| Retrieval-plus-answer time, seconds | {fmt('reflection_on','mean_latency_seconds')} | {fmt('reflection_off','mean_latency_seconds')} |

Off minus on: {delta:+.2f} F1 points. Disabling reflection reduced tokens by {tokens_saved:.1f}%, API calls by {calls_saved:.1f}% and latency by {latency_saved:.1f}%.
After averaging three trials per question, 10,000 paired question bootstrap samples give a conditional interval of [{ci[0]*100:+.2f}, {ci[1]*100:+.2f}] F1 points. This describes this fixed conversation and memory, excludes memory-build variability, and is not a whole-benchmark confidence claim.

![Quality, token usage and latency](comparison.png)

## Category results

| Category | Reflection on F1 | Reflection off F1 |
|---|---:|---:|
'''
    names={1:'Multi-hop',2:'Temporal',3:'Open-domain',4:'Single-hop'}
    for cat in range(1,5):
        a=next(x for x in categories if x['condition']=='reflection_on' and x['category']==cat)
        b=next(x for x in categories if x['condition']=='reflection_off' and x['category']==cat)
        report+=f"| {cat}: {names[cat]} | {a['locomo_f1_mean']*100:.2f} +/- {a['locomo_f1_sd']*100:.2f} | {b['locomo_f1_mean']*100:.2f} +/- {b['locomo_f1_sd']*100:.2f} |\n"
    report+=f'''
## Usage and integrity checks

API calls: {usage['api_calls']:,}; input tokens: {usage['prompt_tokens']:,}; output tokens: {usage['completion_tokens']:,}; total tokens: {usage['total_tokens']:,}; cached input: {usage['cached_input_tokens']:,}.
Price-list estimate: CNY {usage['estimated_off_peak_cny']:.4f}-{usage['charged_upper_cny']:.4f}, within the CNY 9 formal cap (plus CNY 1 reserved for earlier checks). This is not an invoice. Unknown reservations: CNY {usage['unknown_reservations']:.4f}.
Failed/unknown API calls: {usage['failed_or_unknown_api_calls']}; failed question-runs: {sum(r['failed'] for r in rows)}. Failed questions are retained with zero scores. All 240 prescribed unique tuples and category counts were verified; question-level usage matches the ledger. All 454 memory contents and IDs remained unchanged. QA gold/evidence labels were not used to build or retrieve memories.

## Conditions and scope

- Text pipeline from SimpleMem db80b6a plus documented compatibility changes. Exact runtime and protocol: `run_metadata.jsonl`.
- DeepSeek Flash, thinking disabled, planning enabled. Only reflection differs; reflection on permits at most two extra retrieval rounds.
- Complete conv-26 input: 419 turns, 454 pilot-built memories. Ten held-out questions per category 1-4; all eight pilot questions excluded. Selection was fixed before formal answers.
- Qwen3-Embedding-0.6B on CPU, four threads. Two arms run concurrently; retrieval inside each arm is sequential. Timing describes shared load, not isolated single-request latency.
- Output cap 4096 tokens/request; SDK retries zero; timeout 90 seconds. Original application retry logic is retained and every request is metered.
- Primary scoring follows the pinned LoCoMo category-aware rules; original set-token F1 is secondary. Neither is semantic accuracy. Trial means are averaged across three trials; equal category counts make the overall mean equal to the category macro-average.

## Comparison with the reported paper result

Paper Table 1 reports GPT-4.1-mini F1 of 43.46 multi-hop, 58.62 temporal, 19.76 open-domain and 51.12 single-hop, macro-average 43.24. Our reflection-on subset F1 is {on['locomo_f1']['mean']*100:.2f}. Different model, subset and source version prevent a direct numerical reproduction or superiority claim. Our tokens include planning, reflection and final answers; the paper's token accounting must be reconciled before calculating a cross-study saving ratio.

## Files and references

- `questions.csv` / `questions.jsonl`: raw answers, references, both scores, timings, usage and failure flags.
- `trials.csv`, `categories.csv`, `paired_questions.csv`: trial/category/paired aggregates.
- `api_ledger.jsonl`: persistent pre-request reservations and returned usage, without credentials.
- `run_metadata.jsonl`: fixed selection, protocol, code/data/memory hashes and runtime state.
- `analysis.jsonl`, `comparison.png`, `comparison.svg`: numerical analysis and figures.
- [Paper](https://arxiv.org/html/2601.02553v3), [SimpleMem](https://github.com/aiming-lab/SimpleMem), [pinned LoCoMo scorer]({protocol['scorer_source']}), [official pricing](https://api-docs.deepseek.com/quick_start/pricing/).
'''
    discussion=OUT/'DISCUSSION.md'
    if discussion.exists():report+='\n'+discussion.read_text()
    (OUT/'RESULTS.md').write_text(report)
    print(json.dumps(findings,indent=2))
    print('Report saved:',OUT/'RESULTS.md')


if __name__=='__main__':main()
