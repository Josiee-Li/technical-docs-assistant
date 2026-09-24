# 代码学习点与文档来源

代码中搜索 `[学习点 W` 可定位全部标注。编号 W1～W8 对应学习手册的第 1～8 周。

每个标注说明：学习内容、当前实现方式、文档来源。下表按周整理，点击代码链接后搜索对应编号即可定位。

原理、计算示例和实现边界见 [知识点讲解](CONCEPTS.md)，可与各周代码标注对照阅读。

## 如何理解来源

- **框架能力**：当前代码确实调用了相应 LlamaIndex API。
- **概念参考／自行实现**：文档用于学习概念，代码为本项目教学实现，不是从文档直接复制，也未调用其全部封装。
- **项目工程实现／Python 标准库／第三方库**：配置、锁、快照、API 等工程能力，避免误认为属于 LlamaIndex。
- 中文链接来自你提供的中文文档站；当前英文文档入口为 https://developers.llamaindex.ai/python/framework/ 。中文页与当前 API 可能不同，以 uv.lock 的版本及英文文档为准。
- 文档来源是学习参考，不表示每段项目代码都有官方等价示例。

## 学习点清单

| 编号 | 学习内容 | 对应代码 | 实现类别 | 文档来源 |
|---|---|---|---|---|
| W1-01 | 配置与模型职责 | [config.py](../src/doc_assistant/config.py) | 项目工程实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/understanding/rag/) |
| W1-02 | Embedding 接口与测试替身 | [models.py](../src/doc_assistant/models.py) | 框架接口／自行实现 | [阅读文档](https://developers.llamaindex.ai/python/framework/module_guides/models/embeddings/) |
| W1-03 | 真实 Embedding 接入 | [models.py](../src/doc_assistant/models.py) | 框架能力 | [阅读文档](https://developers.llamaindex.ai/python/framework/integrations/embeddings/ollama_embedding/) |
| W1-04 | LLM 接入 | [models.py](../src/doc_assistant/models.py) | 框架能力 | [阅读文档](https://developers.llamaindex.ai/python/framework/integrations/llm/ollama/) |
| W1-05 | Node 到向量索引 | [indexing.py](../src/doc_assistant/indexing.py) | 框架能力 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/getting_started/starter_example/) |
| W2-01 | Document、稳定 ID 与元数据 | [indexing.py](../src/doc_assistant/indexing.py) | 框架能力 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/documents_and_nodes/) |
| W2-02 | 分块与重叠 | [indexing.py](../src/doc_assistant/indexing.py) | 框架能力 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/node_parsers/modules/) |
| W3-01 | 索引配置一致性 | [indexing.py](../src/doc_assistant/indexing.py) | 项目工程实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/) |
| W3-02 | 构建互斥 | [indexing.py](../src/doc_assistant/indexing.py) | Python 标准库 | [阅读文档](https://docs.python.org/zh-cn/3/library/os.html#os.open) |
| W3-03 | StorageContext 与索引恢复 | [indexing.py](../src/doc_assistant/indexing.py) | 框架能力 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/) |
| W3-04 | 增量维护 | [indexing.py](../src/doc_assistant/indexing.py) | 框架 API／项目编排 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/indexing/document_management/) |
| W3-05 | 持久化与快照发布 | [indexing.py](../src/doc_assistant/indexing.py) | 框架 API／项目工程实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/) |
| W3-06 | 向量召回与元数据过滤 | [retrieval.py](../src/doc_assistant/retrieval.py) | 框架能力 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/querying/retriever/) |
| W4-01 | 检索评估与粒度 | [evaluation.py](../src/doc_assistant/evaluation.py) | 概念参考／自行实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/retrieval/retriever_eval/) |
| W4-02 | 检索评估与回答评估的边界 | [evaluation.py](../src/doc_assistant/evaluation.py) | 评估设计 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/evaluating/) |
| W5-01 | 词项与分词 | [models.py](../src/doc_assistant/models.py) | 概念参考／自行实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/bm25_retriever/) |
| W5-02 | BM25 词法检索 | [retrieval.py](../src/doc_assistant/retrieval.py) | 概念参考／自行实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/bm25_retriever/) |
| W5-03 | RRF 排序融合 | [retrieval.py](../src/doc_assistant/retrieval.py) | 概念参考／自行实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/reciprocal_rerank_fusion/) |
| W5-04 | CrossEncoder 重排 | [retrieval.py](../src/doc_assistant/retrieval.py) | 第三方库 | [阅读文档](https://www.sbert.net/docs/cross_encoder/usage/usage.html) |
| W6-01 | 多轮问题改写 | [service.py](../src/doc_assistant/service.py) | 概念参考／自行编排 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/examples/chat_engine/chat_engine_condense_plus_context/) |
| W6-02 | 证据与引用编号 | [service.py](../src/doc_assistant/service.py) | 概念参考／自行实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/examples/query_engine/citation_query_engine/) |
| W6-03 | 基于证据生成回答 | [service.py](../src/doc_assistant/service.py) | 概念参考／自行实现 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/querying/response_synthesizers/) |
| W6-04 | 真实流式生成 | [service.py](../src/doc_assistant/service.py) | 框架 API／项目协议 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/module_guides/deploying/query_engine/streaming/) |
| W7-01 | 确定性的计算工具 | [advanced.py](../src/doc_assistant/advanced.py) | Python 标准库 | [阅读文档](https://docs.python.org/zh-cn/3/library/ast.html) |
| W7-02 | 函数作为工具 | [advanced.py](../src/doc_assistant/advanced.py) | 框架能力 | [阅读文档](https://developers.llamaindex.ai/python/framework/understanding/agent/tools/) |
| W7-03 | 模型驱动的工具选择 | [advanced.py](../src/doc_assistant/advanced.py) | 框架能力 | [阅读文档](https://developers.llamaindex.ai/python/framework/understanding/agent/) |
| W7-04 | Workflow 事件模型 | [advanced.py](../src/doc_assistant/advanced.py) | 框架能力 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/understanding/workflows/basic_flow/) |
| W7-05 | 条件分支与有界重试 | [advanced.py](../src/doc_assistant/advanced.py) | 框架 API／项目策略 | [阅读文档](https://docs.llamaindex.org.cn/en/stable/understanding/workflows/branches_and_loops/) |
| W7-06 | 工具调用的契约测试 | [test_project.py](../tests/test_project.py) | 测试替身 | [阅读文档](https://docs.pytest.org/en/stable/how-to/monkeypatch.html) |
| W8-01 | 请求模型与边界校验 | [api.py](../src/doc_assistant/api.py) | 第三方 Web 框架 | [阅读文档](https://fastapi.tiangolo.com/tutorial/body/) |
| W8-02 | 流式 HTTP 响应 | [api.py](../src/doc_assistant/api.py) | 第三方 Web 框架 | [阅读文档](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) |
| W8-03 | 命令行与应用分层 | [cli.py](../src/doc_assistant/cli.py) | Python 标准库 | [阅读文档](https://docs.python.org/zh-cn/3/library/argparse.html) |
| W8-04 | 隔离测试与回归验证 | [test_project.py](../tests/test_project.py) | 测试工程 | [阅读文档](https://docs.pytest.org/en/stable/how-to/tmp_path.html) |

## 建议阅读顺序

先阅读 W1 的模型与索引，再顺着 W2 文档处理 → W3 持久化 → W4 评估 → W5 检索优化 → W6 回答 → W7 Agent/Workflow → W8 应用入口与测试。

每读到一个学习点，先解释它在数据流中的输入和输出，再打开对应文档，最后完成 [8 周学习手册](LEARNING.md) 的练习。

## 尚未直接使用的框架封装

| 框架封装 | 当前状态 | 后续练习 |
|---|---|---|
| IngestionPipeline | 使用 SentenceSplitter 手工编排 | 第 2 周改用 Pipeline 并比较行为 |
| BM25Retriever / QueryFusionRetriever | 手写 BM25 / RRF | 第 5 周替换为官方封装并比较排序 |
| ResponseSynthesizer / CitationQueryEngine / ChatEngine | 显式实现上下文、引用与问题改写 | 第 6 周替换并验证引用和多轮行为 |
| RetrieverEvaluator | 手算文档级指标 | 第 4 周改为片段标注并接入官方评估 |
| Chroma | 使用 SimpleVectorStore | 第 3 周迁移后重新验证更新一致性 |
