import math
from collections import Counter
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from .models import tokens


# [学习点 W5-02] 第 5 周：BM25 词法检索（概念参考／自行实现）
# 学习内容：根据词频、逆文档频率和长度归一化打分；这里是教学公式实现，没有调用官方 BM25Retriever。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/examples/retrievers/bm25_retriever/
def bm25(nodes, query):
    query_tokens = set(tokens(query))
    counts = [Counter(tokens(n.text)) for n in nodes]
    lengths = [sum(c.values()) for c in counts]
    avg = sum(lengths) / len(lengths) if lengths else 1
    result = []
    for node, count, length in zip(nodes, counts, lengths):
        score = 0.0
        for term in query_tokens:
            frequency = count[term]
            if not frequency:
                continue
            df = sum(term in c for c in counts)
            idf = math.log(1 + (len(nodes)-df+0.5)/(df+0.5))
            score += idf * frequency * 2.5 / (frequency + 1.5*(0.25+0.75*length/(avg or 1)))
        if score > 0:
            result.append(NodeWithScore(node=node, score=score))
    return sorted(result, key=lambda n: n.score, reverse=True)


def retrieve(index, question, config, source=None):
    nodes = [n for n in index.docstore.docs.values() if hasattr(n, "text")
             and (source is None or n.metadata.get("source") == source)]
    if not nodes:
        return []
    candidate_k = min(len(nodes), max(config.top_k*3, 10))
    lexical = bm25(nodes, question)[:candidate_k] if config.retrieval != "dense" else []
    dense = []
    if config.retrieval != "bm25":
        # [学习点 W3-06] 第 3 周：向量召回与元数据过滤（框架能力）
        # 学习内容：as_retriever 设置候选数；MetadataFilters 限定来源，再调用 retrieve 返回 NodeWithScore。
        # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/querying/retriever/
        filters = MetadataFilters(filters=[MetadataFilter(key="source", value=source)]) if source else None
        dense = index.as_retriever(similarity_top_k=candidate_k, filters=filters).retrieve(question)
    # [学习点 W5-03] 第 5 周：RRF 排序融合（概念参考／自行实现）
    # 学习内容：按节点 ID 合并两路结果，累加 1/(60+排名)；这是自行实现的 RRF，不直接相加两种检索原始分数。
    # 文档来源：https://docs.llamaindex.org.cn/en/stable/examples/retrievers/reciprocal_rerank_fusion/
    if config.retrieval == "hybrid":
        scores, lookup = {}, {}
        for ranking in (dense, lexical):
            for rank, item in enumerate(ranking, 1):
                key = item.node.node_id
                lookup[key] = item.node
                scores[key] = scores.get(key, 0) + 1/(60+rank)
        results = [NodeWithScore(node=lookup[k], score=v) for k,v in sorted(scores.items(), key=lambda p:p[1], reverse=True)]
    else:
        results = dense if config.retrieval == "dense" else lexical
    # [学习点 W5-04] 第 5 周：CrossEncoder 重排（第三方库）
    # 学习内容：对问题和片段联合打分后排序；这里直接使用 sentence-transformers，不是 LlamaIndex 后处理器类。
    # 文档来源：https://www.sbert.net/docs/cross_encoder/usage/usage.html
    if config.rerank_model and results:
        from sentence_transformers import CrossEncoder
        # 教学实现，生产环境应复用加载后的模型。
        model = CrossEncoder(config.rerank_model)
        values = model.predict([(question, item.node.text) for item in results])
        results = [NodeWithScore(node=item.node, score=float(score)) for item, score in zip(results, values)]
        results.sort(key=lambda item: item.score, reverse=True)
    return results[:config.top_k]
