import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


# [学习点 W1-01] 第 1 周：配置与模型职责（项目工程实现）
# 学习内容：集中管理 LLM、Embedding、切分与检索参数；此 Config 是项目配置类，不是 LlamaIndex Settings。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/understanding/rag/
@dataclass(frozen=True)
class Config:
    mode: str = "demo"
    data_dir: Path = Path("data")
    storage_dir: Path = Path(".storage")
    chunk_size: int = 400
    chunk_overlap: int = 60
    top_k: int = 4
    retrieval: str = "hybrid"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    embed_model: str = "nomic-embed-text"
    rerank_model: str = ""

    def __post_init__(self):
        if self.mode not in {"demo", "ollama"}:
            raise ValueError("APP_MODE 必须是 demo 或 ollama")
        if self.retrieval not in {"dense", "bm25", "hybrid"}:
            raise ValueError("RETRIEVAL 必须是 dense、bm25 或 hybrid")
        if not 0 <= self.chunk_overlap < self.chunk_size or self.chunk_size < 32:
            raise ValueError("分块参数必须满足 chunk_size >= 32 且 0 <= overlap < size")
        if not 1 <= self.top_k <= 20:
            raise ValueError("TOP_K 必须为 1～20")

    @classmethod
    def from_env(cls):
        load_dotenv()
        return cls(
            mode=os.getenv("APP_MODE", "demo"),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            storage_dir=Path(os.getenv("STORAGE_DIR", ".storage")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "400")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "60")),
            top_k=int(os.getenv("TOP_K", "4")),
            retrieval=os.getenv("RETRIEVAL", "hybrid"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            llm_model=os.getenv("LLM_MODEL", "qwen2.5:7b"),
            embed_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            rerank_model=os.getenv("RERANK_MODEL", ""),
        )
