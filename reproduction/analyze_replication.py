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
    state=json.loads((RUN/'summary.json').read_text())
    if not state['completed']:raise SystemExit('Replication incomplete; preserve partial results without claiming completion.')
    plan=json.loads((ROOT/'reproduction/replication_plan.json').read_text())
    protocol=json.loads((ROOT/'reproduction/replication_protocol.json').read_text())
    new=[json.loads(l) for l in (RUN/'questions.jsonl').read_text().splitlines()]
    old=[json.loads(l) for l in (ROOT/'reproduction/results/formal-20261109/questions.jsonl').read_text().splitlines()]
    expected={(t,c,i) for t in range(1,4) for c in CONDITIONS for i in plan['question_indices']}
    assert len(new)==240 and {(r['trial'],r['condition'],r['qa_index']) for r in new}==expected
    assert Counter((r['trial'],r['condition'],r['category']) for r in new)==Counter({(t,c,k):10 for t in range(1,4) for c in CONDITIONS for k in range(1,5)})
    ledger=BudgetLedger(RUN/'api_ledger.jsonl',4.5)
    total=ledger.summary()
    query_events={i:e for i,e in ledger.events.items() if e['stage']!='build_memory'}
    memory_events={i:e for i,e in ledger.events.items() if e['stage']=='build_memory'}
    assert sum(r['usage']['api_calls'] for r in new)==len(query_events)
    assert sum(r['usage']['total_tokens'] for r in new)==sum(e.get('total_tokens',0) for e in query_events.values())
    assert total['charged_upper_cny']<=4.5 and state['memory_unchanged']
    OUT.mkdir(parents=True,exist_ok=True)
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
    report='''# 新对话验证与合并结果

本次在原始实验之外，对另一组完整长对话进行了相同设置的复验。原始结果保留，新结果单独报告，再计算合并结果。

## 范围

- 原始 conv-26：419 轮对话、40 道题、两组各三轮，240 次问题运行。
- 新增 conv-49：509 轮对话、40 道题、两组各三轮，新增 240 次问题运行。
- 合计：两组对话、80 道不同问题、480 次问题运行；每组对话各类别 1–4 均为 10 题。
- 新对话在满足每类至少 10 题的未用对话中，按文本与图片说明字符数最少的规则选择，以适应预算；选题与模型、评分在新结果产生前固定，没有按成绩选择对话。
- 复用原实验问答程序，保持 DeepSeek Flash、关闭 thinking、开启 planning、两组并发、CPU 4 线程和 4096 token 输出上限；两组仅 reflection 开关不同。

## 按对话与合并结果

| 数据范围 | 开启反思 F1 | 关闭反思 F1 | 关闭减开启（分） | token 减少 | 耗时减少 |
|---|---:|---:|---:|---:|---:|
'''
    labels={'conv-26':'原始对话','conv-49':'新增对话','combined':'合并两组'}
    for sid in stats:
        g=stats[sid];d=g['comparison']
        report+=f"| {labels[sid]} | {g['reflection_on']['f1']['mean']*100:.2f} | {g['reflection_off']['f1']['mean']*100:.2f} | {d['f1_off_minus_on_points']:+.2f} | {d['token_saving_percent']:.1f}% | {d['latency_saving_percent']:.1f}% |\n"
    report+='\n分数为三轮平均；不是答对率。每轮先在各对话上汇总，再对轮次求均值。两组题量相同，因此合并结果对两组对话赋予相同权重。\n\n![两组对话合并对比](comparison.png)\n'
    g=stats['combined']
    report+=f'''\n## 合并结果的波动与限制

官方规则 F1：开启反思 {g['reflection_on']['f1']['mean']*100:.2f} ± {g['reflection_on']['f1']['sd']*100:.2f}，关闭反思 {g['reflection_off']['f1']['mean']*100:.2f} ± {g['reflection_off']['f1']['sd']*100:.2f}；± 为三轮样本标准差。
对每题先平均三轮，再进行 10000 次题目级成对 bootstrap，关闭减开启的描述性区间为 [{interval[0]:+.2f}, {interval[1]:+.2f}] 分，条件是这两组固定对话和记忆。
只有两组对话，且新增对话为成本受限选择，不能推广到全部 LoCoMo 或声称质量不受影响。每份记忆仅构建一次，不评估记忆构建的随机性。
两组问答同时运行，耗时是在固定并发负载下测得；跨对话的绝对时间还受运行时段影响。
F1 为词语匹配指标，保留作者原始 set-token F1 作为辅助结果，全部原始答案可供核查。

## 新增费用与核对

新增构建与问答共调用 {total['api_calls']} 次，消耗 {total['total_tokens']:,} token；其中记忆构建 {len(memory_events)} 次，问答 {len(query_events)} 次。
新增费用按官方空闲/高峰价估算 {total['estimated_off_peak_cny']:.4f}–{total['charged_upper_cny']:.4f} 元，构建和问答均计入同一 4.5 元上限，不包括之前已完成的实验。
费用是根据服务端 usage 的估算，实际扣费以平台账单为准；未知费用预留 {total['unknown_reservations']:.4f} 元。
API 失败/未知用量 {total['failed_or_unknown_api_calls']} 次，标记失败的问题 {sum(r['failed'] for r in new)} 次；240 个新增问题组合完整，逐题用量与账本一致，前后记忆一致。

## 结果与来源

- condition_summary.csv：按对话与合并结果，含均值、三轮标准差。
- questions.csv：两组对话全部 480 次回答、参考、评分与用量。
- questions.jsonl / api_ledger.jsonl：新增实验的原始回答与持久费用账本。
- run_metadata.jsonl / build_summary.jsonl：固定参数和记忆构建记录。
- [原始实验结果](../formal-20261109/RESULTS.md)、[LoCoMo 数据](https://github.com/snap-research/locomo)、[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。
'''
    notes=OUT/'DISCUSSION.md'
    if notes.exists():report+='\n'+notes.read_text()
    (OUT/'RESULTS.md').write_text(report)
    print(json.dumps(results,indent=2));print('Report:',OUT/'RESULTS.md')


if __name__=='__main__':main()
