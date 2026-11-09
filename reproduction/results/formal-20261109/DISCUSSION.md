## 如何解读

本子集的主要观察是：关闭反思明显减少了 token 与请求次数，平均 F1 只下降 0.15 分。成对区间跨越 0，因此不能据此认定质量有确定提升或证明质量完全不受影响。
10 道题的三轮平均 F1 在关闭反思后较高，8 道较低，22 道相同；有些题确实从补充检索中受益。

例如问题 24 问 Melanie 如何减压，参考是 Running, pottery。第一轮关闭反思只回答 She runs.（F1 0.333），开启反思包含 running 和 pottery（F1 1.000），但同时列出了更多活动。
问题 32 问 Caroline 参加过哪些 LGBTQ+ 活动：第一轮开启反思的答案更长，列出很多活动和日期，F1 为 0.340；关闭反思答案较短，F1 为 0.600。这里分数变化同时受检索内容和词语匹配方式影响。
LoCoMo 的多答案评分按每个参考子答案取预测中的最佳匹配，对额外列出的答案项惩罚有限。F1 不是人工语义正确率，满分也不保证每个额外细节都正确。
本次未增加付费语义裁判；保留全部原始回答，供报告中的定性分析与人工检查。


## 恢复同一份记忆并重新运行

本目录还包含 fixed_memories.jsonl、memory_db_snapshot.zip 和 snapshot_manifest.jsonl，保留本次固定的文本记忆、检索向量和索引；都是公开基准衍生数据，不含密钥。
在新的检出目录完成依赖、配置、数据与检索模型准备后，运行 `.venv/bin/python reproduction/restore_formal_memory.py` 恢复完全相同的记忆，再运行 `.venv/bin/python reproduction/run_formal.py`。恢复记忆本身不调用大模型 API。
`reproduction/analyze_formal.py` 可以离线重新生成本页、表格和图。本文的定性解释段是核查本次原始回答后添加的说明。
