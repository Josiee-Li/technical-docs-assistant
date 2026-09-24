# LlamaIndex 技术文档助手

代码已添加 `[学习点 W1-01]` 等中文标注，包含学习内容、实现边界和文档链接。阅读时配合 [代码学习点与文档来源](docs/CODE_MAP.md) 定位。

通过一个项目学习文档处理、索引维护、检索、评估、对话、Agent 和 Workflow。

**先运行 demo，再接入真实模型，最后按学习手册逐步实验。** demo 使用可复现的哈希向量和原文摘录，不具有真实语义能力，不代表大模型问答质量。示例 Atlas 系统完全虚构。

## 快速开始

需要 Python 3.11+ 和 uv。在本目录执行：

```bash
uv sync --extra dev
uv run doc-assistant ingest
uv run doc-assistant ask "connect_timeout 默认值是多少？"
uv run doc-assistant eval --output "reports/baseline.json"
uv run pytest -q
```

默认模式为 demo，不需要 API key 或模型服务。首次安装依赖需要网络；安装完成后的 demo 检索、问答和评估不调用远程模型。若没有 uv，可在虚拟环境内使用 `python -m pip install -e '.[dev]'`，随后直接运行 `doc-assistant`。

## 真实模型：Ollama

### Bash 启停脚本（Linux）

仓库提供独立的 Ollama 启停脚本，默认查找 `~/apps/ollama/bin/ollama`。
其他安装路径可通过 `OLLAMA_BIN` 指定：

```bash
./scripts/ollama/start.sh
./scripts/ollama/stop.sh
# 例如：OLLAMA_BIN=/usr/local/bin/ollama ./scripts/ollama/start.sh
```

脚本检测到已经运行的 Ollama 服务时不会接管该进程；停止脚本只停止由它启动并记录的进程。
也可以在另一个终端直接运行 `ollama serve`，结束时按 `Ctrl+C`。

项目根目录提供以下入口，脚本也支持从其他目录调用：

```bash
./start.sh cli ingest                 # 首次使用或文档修改后构建索引
./start.sh cli                        # 前台交互对话，/quit 或 Ctrl+C 退出
./start.sh cli ask "连接超时默认值是多少？"
./start.sh cli --mode demo chat       # 临时使用 demo 模式
./start.sh web                        # 后台启动浏览器交互页面和 API
PORT=8010 ./start.sh frontend         # web 的别名，可指定端口
./stop.sh                            # 停止脚本启动的命令行和 Web 进程
./stop.sh web                        # 仅停止 Web；也支持 cli
```

当前项目没有独立前端，浏览器入口为 FastAPI 交互文档：
http://127.0.0.1:8001/docs，可展开 `/query` 点击 Try it out 进行问答。
脚本默认用 8001 端口，避免与其他 8000 服务冲突。
依赖需先通过 `uv sync --extra dev` 安装；模型需要单独下载。
项目脚本使用现有 `.env`，不自动构建索引或启动 Ollama。
Web 日志位于项目 `.run/web.log`。项目停止脚本只管理自身记录的命令行和 Web 进程，
不会停止共享的 Ollama 服务。Ollama 脚本的日志位于 `scripts/ollama/.run/ollama.log`。
这些脚本依赖 Bash、curl 和 flock，并通过 Linux 的 `/proc` 跟踪进程。

本项目不自动安装 Ollama 或下载大模型。已有 Ollama 服务时，可按机器内存选择模型；下面仅为示例：

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

复制 `.env.example` 为 `.env`，将 `APP_MODE=ollama`，并建议设置独立的 `STORAGE_DIR=.storage-ollama`。然后执行：

```bash
uv run doc-assistant ingest
uv run doc-assistant ask "开发和生产环境有什么区别？"
uv run doc-assistant chat
uv run doc-assistant agent "标准请求 2500 次需要多少钱？请说明依据。"
uv run doc-assistant workflow "生产环境应该如何配置连接超时？"
```

`LLM_MODEL` 和 `EMBED_MODEL` 可替换成 Ollama 已安装模型。`nomic-embed-text` 只是接入示例，对中文的效果需自行评估。Agent 需要模型支持工具调用。服务默认地址为 `http://localhost:11434`。

切换模式、Embedding 模型或分块配置后必须重新 ingest。文档变更后也需要主动 ingest；当前没有文件监听。模型同名但内容发生变化时，请使用新的存储目录重建索引。

## 功能入口

| 命令或接口 | 能力 |
|---|---|
| `doc-assistant ingest` | 导入 UTF-8 Markdown/TXT，增量更新、删除、无变更跳过 |
| `doc-assistant ask "问题"` | 问答，返回来源文本、节点 ID 和分数 |
| `doc-assistant ask "问题" --source "02-configuration.md"` | 按精确相对文件名过滤 |
| `doc-assistant chat` | 多轮对话；`/reset` 清除历史，`/quit` 退出 |
| `doc-assistant eval --output "reports/baseline.json"` | 文档级检索命中率、Recall@k 和 MRR |
| `doc-assistant workflow "问题"` | 事件驱动检索、证据判断、最多一次改写重试 |
| `doc-assistant agent "问题"` | 检索与计算工具，最多 8 次迭代；仅 Ollama |
| `doc-assistant serve` | 启动本地 FastAPI 服务 |

可在命令前使用 `--mode demo` 或 `--mode ollama` 临时覆盖配置，例如 `doc-assistant --mode demo ingest`。

## API

```bash
uv run doc-assistant serve
```

交互文档：http://127.0.0.1:8000/docs

```bash
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"连接超时默认值是多少？"}'

curl -N -X POST "http://127.0.0.1:8000/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"question":"生产环境如何配置？"}'
```

流式接口返回 NDJSON，每行一个事件：`sources`、`delta`、`done` 或 `error`。真实模型逐段输出；demo 只输出证据摘录，不模拟 token 流。

多轮请求通过 `history` 传入最多 6 条 `user` / `assistant` 消息。API 不保存会话，因此不同请求间不会共享聊天历史。demo 仅拼接上一个用户问题，真实模式才使用模型改写独立问题。

`/health` 只表示进程正常，不保证索引和模型服务可用。未建立索引或配置不匹配时查询返回 409。服务只绑定本机地址，没有实现用户认证、多租户授权和上传接口。

## 数据与索引

- `data/`：5 份虚构的 Atlas 文档，可以替换成自己的 Markdown/TXT。
- `evaluation/questions.json`：14 道题，其中 12 道有答案、2 道无答案。
- `.storage/`：LlamaIndex 原生 SimpleVectorStore / Docstore 快照，不依赖数据库。
- 稳定文档 ID 使用相对文件路径，内容哈希用于识别修改；未变化文档不重新嵌入。
- 构建时先写完整新快照，再原子切换 `CURRENT`。失败时旧快照仍可读取。
- 历史快照不会自动删除，方便观察和恢复，但会占用磁盘。
- `build.lock` 防止并发构建。如果进程被强制终止，确认没有构建进程后再移除遗留锁。

## 检索实验

`.env` 中的 `RETRIEVAL` 可选 `dense`、`bm25`、`hybrid`。默认 hybrid，通过 RRF 融合向量和 BM25 排名。BM25 是可阅读的教学实现，中文采用单字和双字分词，适合小语料；它不是面向大规模部署的倒排索引。

调整 `TOP_K` 不需要重建索引。调整 `CHUNK_SIZE`、`CHUNK_OVERLAP` 需要重新 ingest。不同检索方法的分数含义不同，不应直接比较。

可选 CrossEncoder 重排：

```bash
uv sync --extra dev --extra rerank
```

然后将 `RERANK_MODEL` 设为适合数据语言的模型名，例如 `BAAI/bge-reranker-base`。首次使用需要下载模型。教学实现每次请求加载重排模型，不适合性能敏感服务；模型缓存复用是后续练习。重排的真实模型路径未在无模型环境下实测。

## 评估说明

评估命令只测检索，不调用 LLM 判分。`expected_sources` 标注文件名，因此当前是**文档级**命中、召回和 MRR，不能当成片段级准确率。`reference_answer` 用于人工检查，脚本不会自动使用它判断正确性。

无答案题不会计入召回指标。dense/hybrid 可能对无答案问题仍返回片段；检索到片段不等于证据充分。真实问答依赖提示词约束，Workflow 增加模型证据判断，但都不能保证消除幻觉。请按学习手册补充人工正确性、引用准确性和拒答评估。

## 从哪里读代码

1. `config.py` → `models.py`：配置与模型边界。
2. `indexing.py`：文档、切分、增量更新、持久化。
3. `retrieval.py`：向量检索、BM25、RRF、可选重排。
4. `service.py`：问题改写、证据、提示词、回答和流式生成。
5. `evaluation.py`：检索指标。
6. `advanced.py`：工具、Agent、Workflow。
7. `api.py` / `cli.py`：应用入口。

本项目故意显式构建带编号的上下文并调用 LLM，便于观察数据流；它没有把所有逻辑藏在 QueryEngine 中。将其替换为 ResponseSynthesizer 是学习练习。

详细安排见 [8 周项目学习手册](docs/LEARNING.md)，架构与限制见 [设计说明](docs/ARCHITECTURE.md)。

代码中的中文注释解释关键算法与设计原因；配套 [知识点讲解](docs/CONCEPTS.md) 结合学习文档链接，介绍 RAG、分块、索引更新、检索公式、评估、引用、Agent 与 API。
# technical-docs-assistant
# technical-docs-assistant
# technical-docs-assistant
