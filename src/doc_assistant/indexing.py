import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from .models import embedding


class IndexNotReady(ValueError):
    pass


# [学习点 W3-01] 第 3 周：索引配置一致性（项目工程实现）
# 学习内容：记录影响向量和分块的配置，防止新模型查询旧向量；指纹比较是项目自行增加的约束。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/
def fingerprint(config):
    return {"mode": config.mode, "embedding": "demo-hash-v1" if config.mode == "demo" else config.embed_model,
            "endpoint": config.ollama_url if config.mode == "ollama" else "",
            "chunk_size": config.chunk_size, "chunk_overlap": config.chunk_overlap}


# [学习点 W3-02] 第 3 周：构建互斥（Python 标准库）
# 学习内容：用 O_EXCL 独占创建锁文件，阻止两个进程同时切换索引；这属于 Python 文件操作。
# 文档来源：https://docs.python.org/zh-cn/3/library/os.html#os.open
@contextmanager
def write_lock(directory):
    # 原子排他创建；异常退出遗留时由使用者确认没有构建进程后移除锁文件。
    lock = directory / "build.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("已有构建任务或遗留 build.lock，请确认没有构建进程后处理") from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def current(config):
    pointer = config.storage_dir / "CURRENT"
    if not pointer.exists():
        raise IndexNotReady("尚未构建索引，请先运行 doc-assistant ingest")
    version = pointer.read_text().strip()
    if not version or Path(version).name != version:
        raise IndexNotReady("索引指针格式无效")
    path = config.storage_dir / version
    manifest = json.loads((path / "manifest.json").read_text())
    if manifest["config"] != fingerprint(config):
        raise IndexNotReady("Embedding 或切分配置已变化，请重新运行 ingest")
    return path, manifest


# [学习点 W3-03] 第 3 周：StorageContext 与索引恢复（框架能力）
# 学习内容：StorageContext 连接持久化存储，load_index_from_storage 恢复索引；显式传入相同 Embedding。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/
def load_index(config):
    path, manifest = current(config)
    index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(path)),
                                    embed_model=embedding(config))
    return index, manifest


def ingest(config):
    if not config.data_dir.is_dir():
        raise ValueError(f"文档目录不存在：{config.data_dir}")
    config.storage_dir.mkdir(parents=True, exist_ok=True)
    with write_lock(config.storage_dir):
        documents, hashes = {}, {}
        for path in sorted(config.data_dir.rglob("*")):
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            name = path.relative_to(config.data_dir).as_posix()
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                continue
            hashes[name] = hashlib.sha256(text.encode()).hexdigest()
            # [学习点 W2-01] 第 2 周：Document、稳定 ID 与元数据（框架能力）
            # 学习内容：text 是内容，id_ 使用相对路径，metadata.source 用于过滤与来源展示；读取文件由项目自行实现。
            # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/loading/documents_and_nodes/
            documents[name] = Document(text=text, id_=name, metadata={"source": name})
        old_hashes = {}
        try:
            old_path, manifest = current(config)
            old_hashes = manifest["files"]
        except IndexNotReady:
            old_path = None
        added = sorted(set(hashes) - set(old_hashes))
        removed = sorted(set(old_hashes) - set(hashes))
        changed = sorted(k for k in hashes.keys() & old_hashes.keys() if hashes[k] != old_hashes[k])
        if old_path and not (added or removed or changed):
            return {"status": "unchanged", "documents": len(hashes), "added": [], "changed": [], "removed": []}
        # [学习点 W2-02] 第 2 周：分块与重叠（框架能力）
        # 学习内容：SentenceSplitter 把 Document 转为 Node；chunk_size 与 chunk_overlap 以 tokenizer 的 token 数计。
        # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/loading/node_parsers/modules/
        splitter = SentenceSplitter(chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
        embed = embedding(config)
        if old_path:
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(old_path)), embed_model=embed)
            # [学习点 W3-04] 第 3 周：增量维护（框架 API／项目编排）
            # 学习内容：delete_ref_doc 删除原文档关联节点，insert_nodes 插入更新节点；文件哈希和变更集合由项目维护。
            # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/indexing/document_management/
            for name in removed + changed:
                index.delete_ref_doc(name, delete_from_docstore=True)
            if added or changed:
                nodes = splitter.get_nodes_from_documents([documents[k] for k in added + changed])
                index.insert_nodes(nodes)
        else:
            nodes = splitter.get_nodes_from_documents(list(documents.values()))
            # [学习点 W1-05] 第 1 周：Node 到向量索引（框架能力）
            # 学习内容：VectorStoreIndex 为 Node 生成向量并组织存储；这里使用默认本地存储，不依赖外部向量数据库。
            # 文档来源：https://docs.llamaindex.org.cn/en/stable/getting_started/starter_example/
            index = VectorStoreIndex(nodes, embed_model=embed)
        # [学习点 W3-05] 第 3 周：持久化与快照发布（框架 API／项目工程实现）
        # 学习内容：persist 是框架 API；版本目录和 CURRENT 原子替换是项目策略，确保失败构建不覆盖旧快照。
        # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/
        # 先完整写入新快照，再切换指针。构建失败不会破坏可用的旧快照。
        version = uuid.uuid4().hex
        target = config.storage_dir / version
        index.storage_context.persist(persist_dir=str(target))
        (target / "manifest.json").write_text(json.dumps({"config": fingerprint(config), "files": hashes}, ensure_ascii=False, indent=2))
        pending = config.storage_dir / "CURRENT.tmp"
        pending.write_text(version)
        os.replace(pending, config.storage_dir / "CURRENT")
        return {"status": "built", "documents": len(hashes), "added": added, "changed": changed, "removed": removed}
