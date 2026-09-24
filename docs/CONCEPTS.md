# 从代码理解 RAG：知识点讲解

配合 [8 周学习手册](LEARNING.md) 阅读。下文沿用 [代码来源表](CODE_MAP.md) 的 W1～W8 编号：代码内注释解释局部实现，这里解释原理、例子和实验结果该如何理解。链接是概念参考；手写算法不代表调用了对应框架封装，具体 API 以项目依赖版本为准。

## W1：为什么同时需要 Embedding 和 LLM？

阅读：[RAG 简介](https://docs.llamaindex.org.cn/en/stable/understanding/rag/)、[基础示例](https://docs.llamaindex.org.cn/en/stable/getting_started/starter_example/)。代码：[models.py](../src/doc_assistant/models.py)、[service.py](../src/doc_assistant/service.py)。

RAG（检索增强生成）先从外部资料中找证据，再将证据放进提示词生成回答。导入文档并不训练或修改 LLM 权重；更新知识库靠重新导入资料。

Embedding 将文本编码成向量，使问题和相关片段可以通过相似度排序。LLM 接收问题与检索出的文本，生成自然语言回答。例如“连接等待多久会失败？”先召回包含 `connect_timeout` 的片段，再根据其中的数值组织答案。这种同义表达匹配需要合适的真实向量模型，不能用 demo 的表现代替验证。

`DemoEmbedding` 将词项通过 SHA-256 映射到 512 维计数向量，并做 L2 归一化：`v / sqrt(sum(v_i²))`。非零单位向量的点积等于余弦相似度。相同词有相同位置，不同词可能碰撞；它没有学习同义词关系。固定哈希适合离线复现，而 Python 内置字符串 `hash()` 默认不保证跨进程结果相同。

文档向量与查询向量必须处于兼容的空间。即使两个模型输出维数一样，也不能混用。更换 Embedding 要重新 ingest；更换只负责生成的 LLM 不需要重建向量。

## W2：Document、Node 和分块重叠

阅读：[Document / Node](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/documents_and_nodes/)、[切分器](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/node_parsers/modules/)、[Ingestion Pipeline](https://docs.llamaindex.org.cn/en/stable/module_guides/loading/ingestion_pipeline/)。代码：[indexing.py](../src/doc_assistant/indexing.py) 的 W2-01、W2-02。

`Document` 表示一份原始资料，`Node` 是可独立检索的片段。这里一份 Markdown 文件对应一个 Document，切分后的 Node 继承来源元数据并关联原文档。`metadata.source` 保存相对文件名，用于过滤、显示出处和评估；它不是虚构的页码，也不是授权信息。

`chunk_size=400` 指 tokenizer 的 token 数，不是 400 个汉字。SentenceSplitter 尽量保持句子边界，并为元数据保留预算。`chunk_overlap=60` 让相邻块保留部分重复上下文，例如避免将“该超时配置”和“默认 10 秒”完全割裂。重叠越大，重复存储与上下文开销也可能越大，并不保证效果更好。

块太小可能丢失条件，块太大可能混入无关内容。学习手册中 200/400/800 的实验应固定模型、题库和检索方式，每次重新 ingest，再查看跨边界问题的召回结果。当前项目直接编排读取和切分，没有使用 IngestionPipeline；后者可将转换步骤组织成管线。

## W3：增量更新为什么还要保存完整快照？

阅读：[持久化](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/)、[向量存储](https://docs.llamaindex.org.cn/en/stable/module_guides/storing/vector_stores/)。代码：[indexing.py](../src/doc_assistant/indexing.py) 的 W3-01～W3-05。

文件路径作为稳定文档 ID，内容 SHA-256 用于识别变化。新增文件需要生成节点和向量；修改文件先删除关联的旧节点，再插入新节点；删除文件移除旧节点。重命名等价于删除旧路径、新增新路径。空白文件被忽略，因此原有文件变空也会从索引移除。

“增量”指只对变化内容重新处理，不表示磁盘只写变化部分。当前 SimpleVectorStore 在内存中完成更新，再把整份索引持久化到新的版本目录，最后通过 `os.replace` 切换 `CURRENT`。读者只读取一次指针，因而加载的是同一版本的索引和 manifest；发布前失败仍可读取旧版本。

`build.lock` 用排他创建阻止并发写者。这是项目的文件系统策略，不是 LlamaIndex 自带的数据库事务。原子替换保证可见性，未执行 `fsync` 的实现不提供完整断电持久性保证；旧快照也没有自动清理。迁移到共享向量数据库时，修改可能立即对其他读者可见，需要重新设计版本与发布机制。

manifest 中的配置指纹检查模型、端点和分块参数。`top_k` 只改变查询，故不影响指纹。模型同名但权重变化无法靠名称识别，应使用新的存储目录重建。

## W4：Hit Rate、Recall@k 和 MRR 分别回答什么？

阅读：[检索评估](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/retrieval/retriever_eval/)、[忠实性](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/faithfulness_eval/)、[正确性](https://docs.llamaindex.org.cn/en/stable/examples/evaluation/correctness_eval/)。代码：[evaluation.py](../src/doc_assistant/evaluation.py)。

假设某题期望来源为 `{A, B}`，前 3 个片段的来源依次为 `[C, A, A]`：

| 指标 | 当前项目计算方式 | 示例 |
|---|---|---|
| Hit | 至少召回一个期望来源则为 1，否则为 0 | 1 |
| Recall@k | 召回的不同期望来源数 / 期望来源总数 | 1/2 |
| RR | 首个相关片段排名的倒数，未命中为 0 | 1/2 |

对有答案题逐题等权平均，得到 Hit Rate、平均 Recall@k 和 MRR。这里的 `k` 是片段数，相关性标签却是源文件名：Recall 会去重来源，RR 仍保留片段排名，不能解读为对唯一文件排序后的 MRR。命中文件也不一定命中该文件里真正包含答案的片段。

无答案题没有期望来源，Recall 的分母为零，故不纳入这些平均指标。是否正确拒答要另外评估。检索命中率高也不保证生成质量：正确性关注回答是否正确，忠实性关注回答是否受给定证据支持；一段忠实复述过期资料的回答仍可能不正确。当前脚本不调用 LLM 评分，也不使用 `reference_answer` 自动判断回答。

## W5：BM25、向量检索、RRF 和重排

阅读：[BM25](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/bm25_retriever/)、[RRF](https://docs.llamaindex.org.cn/en/stable/examples/retrievers/reciprocal_rerank_fusion/)、[后处理](https://docs.llamaindex.org.cn/en/stable/module_guides/querying/node_postprocessors/)。代码：[retrieval.py](../src/doc_assistant/retrieval.py)。

BM25 依靠词项匹配，适合配置键、错误码等精确表达。项目中文分词同时保留单字和相邻双字，例如“超时”产生“超”“时”“超时”，不等于使用了成熟的中文分词模型。

对每个查询词，代码累加：

```text
IDF = ln(1 + (N - df + 0.5) / (df + 0.5))
得分贡献 = IDF × tf × (k1 + 1) / (tf + k1 × (1 - b + b × length / avg_length))
k1 = 1.5，b = 0.75
```

`N` 是候选片段数，`df` 是含该词的片段数，`tf` 是该词在当前片段出现的次数。IDF 提高稀有词权重；词频饱和避免重复一个词无限线性抬分；长度归一化缓解长文本的天然优势。项目先过滤来源再统计，因此过滤后的 IDF 也会改变。实现每次扫描片段，不是预建倒排索引的生产级 BM25。

真实向量检索侧重语义相似度，BM25 侧重字面匹配。两者分数量纲不同，RRF 只利用排名，对节点累加 `1 / (60 + rank)`。例如一个节点两路都排第 1，得分为 `2/61`；只在一路排第 1，则为 `1/61`。常数 60 平滑排名差异，这个分数不是答案正确率。

CrossEncoder 将“问题、候选片段”一起输入模型，重新判断相关性；这不同于 RRF 的纯排名融合。每路检索先取最多 `max(3 × top_k, 10)` 个候选（不超过片段数），两路合并去重后的候选数可能更多，融合或重排后再截断。扩大候选池可能提高召回，也增加成本；重排只能改善已有候选的顺序，不能补回完全漏掉的证据。

## W6：多轮问题、引用和流式输出

阅读：[多轮检索](https://docs.llamaindex.org.cn/en/stable/examples/chat_engine/chat_engine_condense_plus_context/)、[引用问答](https://docs.llamaindex.org.cn/en/stable/examples/query_engine/citation_query_engine/)、[Response Synthesizer](https://docs.llamaindex.org.cn/en/stable/module_guides/querying/response_synthesizers/)。代码：[service.py](../src/doc_assistant/service.py)。

用户先问“connect_timeout 是什么？”，再问“默认值呢？”，第二句单独检索会缺少主体。真实模式借助最近最多 6 条历史消息改写为独立问题，再检索资料；历史用于理解问题，不能替代文档成为事实证据。demo 只是拼接上一个用户问题。

检索结果按本次排名生成 `[1]`、`[2]` 等编号，并保留原文、来源和节点 ID。生成提示词要求关键事实带引用，但“编号存在”和“被引文本确实支持结论”是两项不同检查。资料中的指令应作为内容处理；提示词边界本身不能提供强制隔离或语义证明。当前没有使用 CitationQueryEngine 或 ResponseSynthesizer 的完整封装。

`stream_complete` 的 `delta` 是新增文本，客户端应顺序拼接。项目协议先发 `sources`，再发多个 `delta`，成功时发 `done`，生成失败时发 `error`。流式减少等待完整回答的时间，不代表模型总计算量更少。

## W7：固定 Workflow 与模型驱动 Agent

阅读：[Agent](https://developers.llamaindex.ai/python/framework/understanding/agent/)、[工具](https://developers.llamaindex.ai/python/framework/understanding/agent/tools/)、[Workflow RAG](https://docs.llamaindex.org.cn/en/stable/examples/workflow/rag/)。代码：[advanced.py](../src/doc_assistant/advanced.py)。

Workflow 的路径由开发者定义：`StartEvent → search → EvidenceEvent → assess`；证据不足时返回 `RetryEvent` 再检索一次，否则返回 `StopEvent`。事件承载数据，步骤的类型声明连接流程。项目用 `attempt` 限定最多重试一次，避免反复改写却没有停止条件。真实模式的证据判断只检查资料能否回答问题，并没有逐句验证候选回答；demo 只判断检索结果非空。

Agent 则让模型决定调用哪个工具、传什么参数。函数名、签名、类型和 docstring 组成工具描述，因此这里的工具 docstring 会影响模型决策。`search_documents` 返回有来源的回答，`calculator` 用 AST 白名单执行四则运算；表达式里的函数调用、属性访问和幂运算不会被允许。浮点计算仍有精度限制，不是财务级十进制计算器。

`asyncio.to_thread` 将同步问答放进线程，避免阻塞异步事件循环；它不减少模型调用成本。trace 记录工具输入输出，便于复核实际动作。脚本化模型测试可以验证框架是否正确调用工具，无法证明真实模型总能选择正确工具。

## W8：API 校验、HTTP 流和测试边界

阅读：[调试与追踪](https://docs.llamaindex.org.cn/en/stable/understanding/tracing_and_debugging/tracing_and_debugging/)、[应用指南](https://docs.llamaindex.org.cn/en/stable/understanding/putting_it_all_together/apps/fullstack_app_guide/)。代码：[api.py](../src/doc_assistant/api.py)、[cli.py](../src/doc_assistant/cli.py)、[tests/test_project.py](../tests/test_project.py)。

CLI 与 FastAPI 复用 Assistant，将输入输出适配与检索算法分开。Pydantic 先校验请求结构，失败返回 422；进入业务代码后，全空白问题会被清理后拒绝并返回 400，缺失索引或配置失配返回 409，未预期的查询失败返回 503。`/health` 只确认应用可响应，不验证索引或模型是否就绪。

流式接口在返回迭代器前完成问题检查和检索，所以这些错误还能用 HTTP 状态码表示。响应开始后生成失败，则通过流内 `error` 事件报告。NDJSON 每行一个 JSON 对象，不是 SSE；网络分片与事件行边界无关，客户端应缓存未完成的行，不能把每次收到的数据块直接视为完整 JSON。

`tmp_path` 隔离每个测试的文档和索引，`monkeypatch` 注入可控失败或模型输出。失败快照测试验证旧索引仍可读取，有界重试测试验证最多两次检索。离线契约测试与真实模型效果评估解决不同问题，两者都应在实验记录里明确标注。
