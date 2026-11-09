# FTEC5660 SimpleMem 复现工作

## 当前阶段

已完成环境准备、合成样例、8 题用量试跑，以及 40 题 × 两种配置 × 三轮的正式实验（240 次问题运行）。

## 原始来源

- 作者仓库：https://github.com/aiming-lab/SimpleMem
- 原始提交：db80b6a7c591e0ea730a058e9f5fc4eb06572299
- 下载后逐文件核对：461 个文件完全一致。
- LoCoMo 数据：https://github.com/snap-research/locomo
- 数据固定提交：3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376
- 数据文件：test_ref/locomo10.json；来源和校验值见 provenance.json。

## 本机使用

1. 注册 https://platform.deepseek.com/ ，创建 API key，查看余额。
2. 双击项目根目录的“配置模型密钥.command”，在本机输入密钥。输入不可见是正常现象。
3. 如需重建数据/模型：运行 `.venv/bin/python reproduction/download_data.py` 与 `.venv/bin/python reproduction/download_embedding.py`。
4. 离线检查：`.venv/bin/python reproduction/check_setup.py`。
5. 下载并检查本地检索模型：`.venv/bin/python reproduction/check_setup.py --embedding`。
6. 单次 API 检查（付费）：`.venv/bin/python reproduction/check_setup.py --api`。
7. 两句合成对话的流程样例（付费）：`.venv/bin/python reproduction/smoke_test.py`。

所有命令均在项目根目录运行。不要把密钥放进聊天或提交到 GitHub。
重建本地配置：将 `reproduction/config.template.py` 复制到项目根目录并命名为 `config.py`；将 `reproduction/deepseek.env.example` 复制为根目录 `.env`，然后运行密钥输入工具。

软件安装：`PIP_CERT=/etc/ssl/cert.pem SSL_CERT_FILE=/etc/ssl/cert.pem REQUESTS_CA_BUNDLE=/etc/ssl/cert.pem .venv/bin/python -m pip install -r reproduction/requirements-text.txt`。
完整安装快照在 requirements-lock.txt 中（安装完成后生成）。

## 暂定实验设计

使用文本 SimpleMem 和固定 LoCoMo 子集。先用少量问题试跑以测量用量，再确定正式规模。
原始配置与关闭 reflection 的配置使用相同问题、模型、提示词和已经构建的记忆；默认重复 3 次。
记录回答 F1、检索/回答时间、API 调用和 token 用量、失败次数；把失败与正确拒答分开。
正式报告需对齐论文的题目类别、评分与平均方式；子集或模型差异必须明确说明，不能宣称复现全量论文数值。
DeepSeek 是模型替换，reflection 开关是后续主要实验变量。
正式实验已完成，固定 40 道未用于试跑的题，两组各三轮；结果见下方正式结果链接。

## 设置与兼容调整

本机为 Apple Silicon，使用独立 Python 3.13 环境。
本地检索模型仍采用作者的 Qwen/Qwen3-Embedding-0.6B。
并发数暂降为 2，避免首次测试大量并行请求。
DeepSeek 当前接口默认启用 thinking，因此兼容调整显式传递开关；两组实验使用同一设置。
Python 证书使用 macOS 系统证书 /etc/ssl/cert.pem，不关闭 TLS 校验。
API key 只保存在本机被忽略的 .env 中，config.py 也被忽略。

## 后续交付

- 实测结果及改动对比。
- 最多 10 页报告，含环境、实验目标、结果、改动、调试记录和限制。
- 自己的 GitHub 仓库，含安装运行说明和清楚的修改记录。
- 最长 15 分钟的 Zoom 录制展示链接。

数据检查：10 组长对话，共 1,986 道问题。类别 1/2/3/4/5 的数量分别为 282/321/96/841/446。第一组对话有 419 轮，因此 --num-samples 1 仍不是几道题的小测试。

## 准备阶段调试记录（2026-11-09）

- ZIP 解压代码与作者提交逐文件完全一致，已建立本地原始快照。
- 原始代码不附带 LoCoMo 数据，从数据作者仓库固定版本补齐。
- Python 的默认 HTTPS 证书配置导致安装失败；为安装及其构建子进程指定系统证书后恢复。
- 文本代码导入和数据检查通过。首次导入评测包时需要构建字体缓存，耗时约两分钟。
- 首轮本地检查 9 项通过、2 项失败，失败原因是没有安装 pylance，导致关键词索引创建被跳过；补装作者清单中的 pylance==0.39.0 后重新检查。
- Hugging Face 连接超时，使用 Qwen 官方魔搭模型，记录文件版本和 SHA-256；大文件采用分段下载，拼接后核对完整校验值。
- DeepSeek 当前模型默认开启 thinking；增加显式开关支持，避免本地配置与实际请求不一致。兼容检查使用模拟 HTTP，无实际 API 调用。

复查结果：`pip check` 无依赖冲突；`tests/test_deepseek_compat.py` 与 `tests/test_vector_store_backend.py` 合计 11 项通过（5.33 秒）。这些是离线功能检查，不是论文实验结果。

检索模型从 Qwen 在魔搭社区发布的同名模型下载（Hugging Face 连接超时），每个文件均核对发布方 SHA-256。文件版本和校验值记录在 provenance.json 的 embedding 字段；本机从 .cache/models/Qwen3-Embedding-0.6B 加载。

本地模型检查发现 torch 2.6.0 在此 Mac 的 Metal/MPS 路径中出现形状推导崩溃。为检索模型加入可选 EMBEDDING_DEVICE 设置，本机显式选择 cpu；模型权重保持同一份，后续两组实验均使用 CPU。

## 准备完成状态

- 依赖安装完成，实际安装版本已固定在 requirements-lock.txt。
- LoCoMo 数据下载、格式与校验值检查通过。
- Qwen 检索模型的所有文件和完整权重校验通过。
- CPU 实际运行通过：一句测试文本生成 1×1024 检索向量。
- 本地数据库与 DeepSeek 请求兼容性共 11 项检查通过。
- API 密钥已由用户在本机配置；连接、完整问答样例和 8 题 LoCoMo 用量测试均已通过，正式重复实验和关闭 reflection 的改动对比也已完成。

## 小规模真实数据用量测试

连接检查已成功返回 OK。两句合成对话的完整流程成功：建立两条记忆，正确回答 Shanghai，耗时 8.79 秒（不含模型初始化）。合成样例不能替代 LoCoMo 实验。

用量测试入口：`.venv/bin/python reproduction/run_pilot.py --dry-run` 只显示固定选题，无 API 调用；去掉 --dry-run 执行小规模基线测试。
默认使用第一组对话 conv-26 的全部 419 轮对话，从类别 1–4 各固定随机选 2 题，共 8 题（seed=5660）；不使用答案或 evidence 构建记忆。类别 5 不在本轮范围内。
保留作者的文本压缩、检索规划、反思和回答提示词。临时限制记忆构建单次输出最多 8192 token、检索/回答单次输出最多 4096 token，关闭 SDK 自动重试，记忆构建并发为 2，检索串行；完整记录实际使用的参数。
每次调用记录服务端 token 用量、缓存命中、耗时、阶段和失败状态，不记录密钥。最多 80 次调用、250000 token 的保守预留上限，达到上限立即停下并保存已有结果。
费用按 2026-11-09 DeepSeek 官方人民币价目表估算，报告空闲/高峰区间，不能代替平台账单。
本轮评分只使用作者脚本的 set-token F1；正式与论文比较前仍须核对官方 LoCoMo 评分和汇总方式。
结果、原始回答、调用用量和可复用的记忆库保存在 test_results/pilot-时间戳 中。本轮不执行 reflection 改动对比或正式重复实验。

最新结果见 [8 题用量试跑报告](results/pilot-20261109/RESULTS.md)。

## 正式结果与重现步骤

- [完整正式结果、对比图与限制](results/formal-20261109/RESULTS.md)：240/240 次问题运行完成，无 API 失败；记忆前后不变。
- 主要结果：开启/关闭反思的官方规则 F1 为 50.62/50.47；关闭后每题 token 减少 62.2%，测得耗时减少 41.0%。这是固定单对话子集的结果，不是总体结论。
- 正式 API 用量 1,933,234 token，按官方空闲/高峰价估算 1.71–3.42 元；包含先前试跑的预算仍在 10 元限制内。
- [实验前固定的设计](FORMAL_PROTOCOL.md)和 formal_protocol.json 保留选题、评分与费用上限。

从新目录重现（命令均在项目根目录）：

```sh
python3 -m venv .venv
PIP_CERT=/etc/ssl/cert.pem SSL_CERT_FILE=/etc/ssl/cert.pem REQUESTS_CA_BUNDLE=/etc/ssl/cert.pem .venv/bin/python -m pip install -r reproduction/requirements-lock.txt
cp reproduction/config.template.py config.py
cp reproduction/deepseek.env.example .env
.venv/bin/python reproduction/setup_key.py
.venv/bin/python reproduction/download_data.py
.venv/bin/python reproduction/download_embedding.py
.venv/bin/python reproduction/restore_formal_memory.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/python -u reproduction/run_formal.py
.venv/bin/python reproduction/analyze_formal.py
```

上述安装方式按本次 macOS/Python 环境记录，系统证书路径可按自己的系统调整。重新运行模型实验会产生 API 费用；只查看已保存结果、恢复快照和离线分析不会产生模型费用。
已有运行会按同一持久账本续跑，完成的 240 个组合不会重复调用；如需全新独立复验，应另建检出目录并保留自己的预算记录。
尚未发布自己的 GitHub 仓库，未生成最终提交版报告或录制展示。
