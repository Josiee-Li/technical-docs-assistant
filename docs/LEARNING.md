# 8 周项目学习手册

代码已添加 `[学习点 W1-01]` 等中文标注，包含学习内容、实现边界和文档链接。阅读时配合 [代码学习点与文档来源](CODE_MAP.md) 定位。

每周 8～10 小时：1 小时阅读、3 小时代码追踪、3 小时修改与实验、1～3 小时复盘。每周记录：假设、配置、结果、失败案例和结论。先保持默认 demo 熟悉流程，再切到 Ollama 评估真实语义与回答质量。

已实现代码是参考实现，不建议一次性阅读全部。每一周先运行已有功能，解释数据流，再完成指定改动。升级 API 时优先核对 [当前官方文档](https://developers.llamaindex.ai/python/framework/)，中文站可能滞后。

## 第 1 周：最小 RAG

阅读：
- [安装](https://docs.llamaindex.org.cn/en/stable/getting_started/installation/)
- [基础示例](https://docs.llamaindex.org.cn/en/stable/getting_started/starter_example/)
- [RAG 简介](https://docs.llamaindex.org.cn/en/stable/understanding/rag/)

运行 `ingest`、`ask`，阅读 `models.py`、`indexing.py` 和 `service.py`。在纸上写出每个阶段的输入输出。

练习：用 5 份自己的文档替换示例，准备 10 道带出处的问题。追踪 `Document → Node → VectorStoreIndex → Retriever → LLM`。分别观察检索片段与最终回答，说明为什么 demo 并非真实语义检索。

验收：能解释 LLM 与 Embedding 的职责、索引何时更新、来源文本在哪里产生。

## 第 2 周：文档处理

阅读：
- [Document / Node](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/documents_and_nodes/)
- [切分器](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/node_parsers/modules/)
- [Ingestion Pipeline](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/ingestion_pipeline/)

当前实现只使用 Document 和 SentenceSplitter；没有预先抽象通用 Pipeline。

练习：比较 200/400/800 token 的切分效果；构造一个答案跨分块边界的问题；添加章节元数据。随后把现有切分封装到 IngestionPipeline，确认行为未变。可选使用 SimpleDirectoryReader 加入 PDF；页码需检查加载器输出，不能手工伪造。

验收：实际查看 20 个片段，指出至少一个坏分块及原因。修改分块参数后重新 ingest。

## 第 3 周：索引维护

阅读：
- [持久化](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/)
- [向量存储](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/vector_stores/)

阅读 `indexing.py` 和 `test_update_delete_and_noop`。观察新增、修改、删除、无变更和失败构建行为。

练习：新增一份文档，再修改并删除它；检查旧信息是否仍被检索。选做：迁移到 Chroma。迁移时特别注意当前 SimpleVectorStore 的原子快照策略不能直接套用共享数据库，必须重新设计更新一致性和过滤。

验收：重启进程能复用索引，无变更时不生成新快照，失败构建不会影响旧索引。

## 第 4 周：评估

阅读：
- [评估](https://docs.llamaindex.org.cn/en/stable/module_guides/evaluating/)
- [检索评估](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/retrieval/retriever_eval/)
- [忠实性](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/faithfulness_eval/)
- [正确性](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/correctness_eval/)

执行 `eval`，手工计算 3 道题的命中、Recall@k 和 MRR，与脚本结果对照。

练习：将题库扩充到 40～60 题，分成调优集和留出集。加入跨文档题、同义表达、无答案题。真实模型模式下人工标注回答正确性、证据支持程度和引用准确性。当前脚本仅实现文档级检索指标，LLM 自动判分是后续扩展。

验收：生成一份基线报告；至少归类 5 个失败案例为解析、切分、召回或生成问题。

## 第 5 周：检索优化

阅读：
- [BM25](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/bm25_retriever/)
- [RRF](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/reciprocal_rerank_fusion/)
- [后处理](https://docs.llamaindex.org.cn/en/stable/module_guides/querying/node_postprocessors/)

比较 `RETRIEVAL=dense`、`bm25`、`hybrid`；分别修改 TOP_K。一次只改变一个主要变量。

练习：真实 Embedding 模式下用相同题库比较三种方案；可选安装 rerank extra，再观察 CrossEncoder 是否改善首位命中率。分析 RRF 排序融合和模型重排的区别。

验收：提交实验表：配置、命中率、MRR、延迟、失败样例。不要用 demo 哈希向量的结果推断模型优劣。

## 第 6 周：回答、引用与对话

阅读：
- [Response Synthesizer](https://docs.llamaindex.org.cn/en/stable/module_guides/querying/response_synthesizers/)
- [引用问答](https://docs.llamaindex.org.cn/en/stable/examples/query_engine/citation_query_engine/)
- [多轮检索](https://docs.llamaindex.org.cn/en/stable/examples/chat_engine/chat_engine_condense_plus_context/)

使用 `chat` 和 `/query/stream`。观察 standalone query、sources、delta。

练习：当前代码是显式的检索上下文加提示词；用 ResponseSynthesizer 实现同样行为并对比。加入引用编号校验，注意编号合法不等于语义支持。对 10 道无答案题测试拒答；测试三轮指代和清空历史。

验收：每个关键结论的引用能支撑原句；记录不能回答的情况，不能将“检索非空”当作通过证据检查。

## 第 7 周：Agent 和 Workflow

阅读：
- [Agent](https://developers.llamaindex.ai/python/framework/understanding/agent/)
- [工具](https://developers.llamaindex.ai/python/framework/understanding/agent/tools/)
- [Workflow RAG](https://docs.llamaindex.org.cn/en/stable/examples/workflow/rag/)

运行 workflow，再接入支持工具调用的 Ollama 模型运行 agent。阅读 `advanced.py`。

练习：输入只需要计算、只需要检索和先检索再计算的请求，观察 trace。构造证据不足案例，确认 Workflow 最多改写重试一次。对比普通 query、Workflow 与 Agent 的调用次数、效果和延迟。

验收：解释为何固定流程适合 Workflow，而开放工具选择适合 Agent。不要增加第三个工具，直到已有两个工具的选择行为经过验证。

## 第 8 周：服务与作品整理

阅读：
- [调试与追踪](https://docs.llamaindex.org.cn/en/stable/understanding/tracing_and_debugging/tracing_and_debugging/)
- [应用指南](https://docs.llamaindex.org.cn/en/stable/understanding/putting_it_all_together/apps/fullstack_app_guide/)

运行 API 和测试，检查缺失索引、空问题、模型服务不可用、流式中断。

练习：补充一个最小网页（选做）；扩展日志中的检索耗时与模型耗时；为一次真实模型实验记录模型版本、机器、语料、指标和成本。当前没有计费统计，不要把总耗时当成模型耗时。

验收：新环境依照 README 可复现；写清哪些实验使用了真实模型，哪些只使用替身或离线演示。产出自己的架构图与失败案例报告。

## 实验记录模板

| 字段 | 内容 |
|---|---|
| 要解决的问题 | |
| 语料与题库版本 | |
| 模型与参数 | |
| 唯一主要变更 | |
| 基线与实验指标 | |
| 失败案例 | |
| 保留或撤回变更的依据 | |
