import hashlib
import math
import re
from llama_index.core.embeddings import BaseEmbedding


# [学习点 W5-01] 第 5 周：词项与分词（概念参考／自行实现）
# 学习内容：BM25 依赖词项匹配；这里自行实现英文单词、中文单字和双字分词，不是框架内置分词器。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/examples/retrievers/bm25_retriever/
def tokens(text: str) -> list[str]:
    # 中文使用单字和相邻双字，英文使用单词；仅用于教学检索。
    parts = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text.lower())
    result = []
    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            result.extend(part)
            result.extend(part[i:i+2] for i in range(len(part)-1))
        else:
            result.append(part)
    return result


# [学习点 W1-02] 第 1 周：Embedding 接口与测试替身（框架接口／自行实现）
# 学习内容：继承 BaseEmbedding 实现查询与文本向量接口；哈希算法只供离线演示，不具有语义理解能力。
# 文档来源：https://developers.llamaindex.ai/python/framework/module_guides/models/embeddings/
class DemoEmbedding(BaseEmbedding):
    """可复现的哈希向量，不具有真实语义能力，不用于效果结论。"""
    model_name: str = "demo-hash-v1"
    dimensions: int = 512

    def _get_text_embedding(self, text):
        vector = [0.0] * self.dimensions
        for token in tokens(text):
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1
        norm = math.sqrt(sum(x*x for x in vector)) or 1
        return [x/norm for x in vector]

    def _get_query_embedding(self, query):
        return self._get_text_embedding(query)

    async def _aget_query_embedding(self, query):
        return self._get_query_embedding(query)


# [学习点 W1-03] 第 1 周：真实 Embedding 接入（框架能力）
# 学习内容：OllamaEmbedding 将文档和问题送入同一向量模型；替换模型后需要重建索引。
# 文档来源：https://developers.llamaindex.ai/python/framework/integrations/embeddings/ollama_embedding/
def embedding(config):
    if config.mode == "demo":
        return DemoEmbedding()
    from llama_index.embeddings.ollama import OllamaEmbedding
    return OllamaEmbedding(model_name=config.embed_model, base_url=config.ollama_url)


# [学习点 W1-04] 第 1 周：LLM 接入（框架能力）
# 学习内容：Ollama 负责文本生成，区别于 embedding() 的向量化职责；温度与超时在此配置。
# 文档来源：https://developers.llamaindex.ai/python/framework/integrations/llm/ollama/
def llm(config):
    from llama_index.llms.ollama import Ollama
    return Ollama(model=config.llm_model, base_url=config.ollama_url,
                  request_timeout=120, temperature=0)
