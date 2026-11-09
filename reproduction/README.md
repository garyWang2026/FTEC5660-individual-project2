# FTEC5660 SimpleMem 复现工作

## 当前阶段

环境准备阶段，尚未产生真实 LoCoMo 实验结果。样例运行不等于完成复现。

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
目前只准备环境，未执行这两组正式实验。

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
- 尚未配置 API 密钥，未执行真实 API 检查、完整问答样例或 LoCoMo 基准实验。
