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
CN={'reflection_on':'开启反思','reflection_off':'关闭反思'}


def mean_sd(values):
    return statistics.mean(values),statistics.stdev(values) if len(values)>1 else 0.0


def csv_file(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def main():
    summary=json.loads((RUN/'summary.json').read_text())
    if not summary['completed']:
        raise SystemExit('Run incomplete; refusing to create a completed-experiment report.')
    protocol=json.loads((RUN/'protocol.json').read_text())
    rows=[json.loads(l) for l in (RUN/'questions.jsonl').read_text().splitlines()]
    expected={(t,c,i) for t in range(1,4) for c in CONDITIONS for i in protocol['question_indices']}
    actual={(r['trial'],r['condition'],r['qa_index']) for r in rows}
    assert len(rows)==len(actual)==240 and actual==expected
    assert Counter((r['condition'],r['trial'],r['category']) for r in rows)==Counter({(c,t,k):10 for c in CONDITIONS for t in range(1,4) for k in range(1,5)})
    ledger=BudgetLedger(RUN/'api_ledger.jsonl',9)
    usage=ledger.summary()
    assert usage['charged_upper_cny']<=9
    assert sum(r['usage']['api_calls'] for r in rows)==usage['api_calls']
    assert sum(r['usage']['total_tokens'] for r in rows)==usage['total_tokens']
    assert summary['memory_unchanged']
    OUT.mkdir(parents=True,exist_ok=True)
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
    report=f'''# SimpleMem 正式复现实验与反思消融结果

日期：2026-11-09。完成 40 道固定题目 × 2 种配置 × 3 轮，共 240 次问题运行。

## 主要结果

| 指标（3 轮均值 ± 样本标准差） | 开启反思 | 关闭反思 |
|---|---:|---:|
| LoCoMo 官方规则 F1（0–100 分） | {fmt('reflection_on','locomo_f1',100)} | {fmt('reflection_off','locomo_f1',100)} |
| 作者原始 set-token F1（0–100 分） | {fmt('reflection_on','upstream_f1',100)} | {fmt('reflection_off','upstream_f1',100)} |
| 每题全部 API token | {fmt('reflection_on','mean_tokens')} | {fmt('reflection_off','mean_tokens')} |
| 每题 API 请求次数 | {fmt('reflection_on','mean_api_calls')} | {fmt('reflection_off','mean_api_calls')} |
| 每题检索与回答时间（秒） | {fmt('reflection_on','mean_latency_seconds')} | {fmt('reflection_off','mean_latency_seconds')} |

关闭反思的 F1 相对开启反思变化为 {delta:+.2f} 分；每题 token 变化为 {-tokens_saved:+.1f}%，API 次数变化为 {-calls_saved:+.1f}%，耗时变化为 {-latency_saved:+.1f}%。
按题目先平均 3 轮，再对 40 道题进行 10,000 次成对 bootstrap，关闭减开启的 F1 条件区间为 [{ci[0]*100:+.2f}, {ci[1]*100:+.2f}] 分。
这是固定这一组对话与这一份记忆的描述性区间，不是整个 LoCoMo 总体的置信结论，也不包含记忆构建的随机性。

![质量、用量与耗时对比](comparison.png)

## 分类结果

| 类别 | 开启反思 F1（分） | 关闭反思 F1（分） |
|---|---:|---:|
'''
    names={1:'多跳',2:'时间',3:'开放域',4:'单跳'}
    for cat in range(1,5):
        a=next(x for x in categories if x['condition']=='reflection_on' and x['category']==cat)
        b=next(x for x in categories if x['condition']=='reflection_off' and x['category']==cat)
        report+=f"| {cat}：{names[cat]} | {a['locomo_f1_mean']*100:.2f} ± {a['locomo_f1_sd']*100:.2f} | {b['locomo_f1_mean']*100:.2f} ± {b['locomo_f1_sd']*100:.2f} |\n"
    report+=f'''
## 用量与执行核对

共 {usage['api_calls']:,} 次 API 请求，输入 {usage['prompt_tokens']:,} token，输出 {usage['completion_tokens']:,} token，总计 {usage['total_tokens']:,} token；缓存输入 {usage['cached_input_tokens']:,} token。
正式实验按官方空闲/高峰费率估算 {usage['estimated_off_peak_cny']:.4f}–{usage['charged_upper_cny']:.4f} 元，未超过正式实验 9 元上限；另预留 1 元覆盖此前试跑与连通样例，总预算上限 10 元。
这是价目表估算，不是平台账单。未知费用预留为 {usage['unknown_reservations']:.4f} 元。
失败或未知用量的 API 请求 {usage['failed_or_unknown_api_calls']} 次；标记失败的问题运行 {sum(r['failed'] for r in rows)} 次。失败运行计 0 分，没有删除失败题。
检查完成 240 个唯一的题目/轮次/配置组合，类别和题数符合预定设计；逐题用量与持久账本完全相符。
实验前后 454 条记忆的内容和 ID 完全一致；没有重新构建记忆或读取答案标注进行检索。

## 条件与复现范围

- 使用 SimpleMem 作者提交 db80b6a 的文本路径，并保留已记录的本地兼容调整；运行版本和参数见 run_metadata.jsonl。
- 使用 DeepSeek Flash，关闭模型 thinking；系统 planning 开启。两组唯一主动改变的系统设置为 reflection 的开关；开启时最多两轮补充检索。
- LoCoMo 第一组对话 conv-26 的完整 419 轮对话，压缩得到试跑阶段的 454 条结构化记忆。正式题目按四个类别各抽 10 题，排除全部 8 道用量试跑题；选题在实验前固定，没有根据正式结果调整。
- 检索模型为 Qwen3-Embedding-0.6B，CPU，4 个线程；两组在每题上同时运行，每组内部检索串行。时间包含共享机器上的固定两组并发负载，不能当作单请求独占机器的时延。
- 每次模型请求输出上限 4096 token，SDK 自动重试关闭，单次超时 90 秒；作者自身的重试逻辑保留且所有请求计费记录在账本中。
- 主要评分按固定版本 LoCoMo 官方规则，辅助评分复用 SimpleMem 原脚本规则；都不代表人工语义正确率。
- 每轮 40 题结果先汇总，再对三轮计算均值和样本标准差；由于各类别题数相等，整体平均也等于四类宏平均。

## 与论文报告的对照

SimpleMem 论文 Table 1 使用 GPT-4.1-mini 的全量结果为：多跳 43.46、时间 58.62、开放域 19.76、单跳 51.12，四类平均 F1 43.24。
本次开启反思的子集结果为 {on['locomo_f1']['mean']*100:.2f} 分，模型、题目分布与代码版本均不同；仅作为条件不同的对照，不能据此宣称复现了该数值或超过论文。
本次 token 统计包含全部检索规划、反思和最终回答的 API 用量，不能未经口径核对就与论文的 token 数字计算节省倍数。

## 结果文件与来源

- questions.csv / questions.jsonl：每个问题运行的原始答案、参考、双评分、时延、用量与失败标记。
- trials.csv：两组各三轮的汇总；categories.csv：分类结果；paired_questions.csv：按题目平均后的成对比较。
- api_ledger.jsonl：每个 API 请求前的预算预留与返回用量，支持核对失败和中断支出；不包含密钥。
- run_metadata.jsonl：固定选题、协议、代码提交、数据和记忆校验值、运行状态。
- analysis.jsonl / comparison.png / comparison.svg：统计结果与可导出图表。
- [论文](https://arxiv.org/html/2601.02553v3)，[SimpleMem 代码](https://github.com/aiming-lab/SimpleMem)，[LoCoMo 评分来源]({protocol['scorer_source']})，[官方人民币价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。
'''
    discussion=OUT/'DISCUSSION.md'
    if discussion.exists():report+='\n'+discussion.read_text()
    (OUT/'RESULTS.md').write_text(report)
    print(json.dumps(findings,indent=2))
    print('Report saved:',OUT/'RESULTS.md')


if __name__=='__main__':main()
