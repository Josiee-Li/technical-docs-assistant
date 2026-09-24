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
    # top_k、检索方式和生成模型不改变已存储的节点向量，因此不要求重建。
    # 模型名不等于权重校验和；同名模型更新后，应换存储目录重新构建。
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
        #   0o600 八进制权限：文件所有者可读可写，组和其他用户无权限；实际权限还受umask限制
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("已有构建任务或遗留 build.lock，请确认没有构建进程后处理") from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        #   unlink() 删除锁文件；missing_ok=True 表示文件已经不存在时不报 FileNotFoundError，但权限不足等其他错误仍会抛出
        lock.unlink(missing_ok=True)


def current(config):
    pointer = config.storage_dir / "CURRENT"
    if not pointer.exists():
        raise IndexNotReady("尚未构建索引，请先运行 doc-assistant ingest")
    # 每次加载只读取一次指针，后续索引与 manifest 均取自同一版本目录。
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
    index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(path)),embed_model=embedding(config))
    return index, manifest


def ingest(config):
    # 整体流程：扫描文档 → 对比旧版本 → 增量更新或全量构建 → 保存新快照 → 发布。
    # config 提供文档目录、索引目录、分块参数和 Embedding 配置；返回值是本次同步摘要。

    # 1. 检查输入目录并准备输出目录。
    # is_dir() 在路径不存在或不是目录时返回 False，避免把错误路径误当成空语料同步。
    if not config.data_dir.is_dir():
        raise ValueError(f"文档目录不存在：{config.data_dir}")
    # parents=True 会补齐父目录；exist_ok=True 允许目录已存在，方便重复执行 ingest。
    config.storage_dir.mkdir(parents=True, exist_ok=True)

    # 2. 取得构建锁。write_lock 执行到 yield 后，才会执行下面整个 with 代码块。
    # 正常结束、提前 return 或抛出普通异常时，都会回到 write_lock 的 finally 删除锁。
    with write_lock(config.storage_dir):
        # 3. 扫描当前语料，构造两份以相对路径为键的字典。
        # documents 保存待切分的 Document 对象；hashes 保存内容摘要，供版本比较和落盘。
        documents, hashes = {}, {}
        # rglob("*") 递归枚举子目录中的路径；sorted 让处理顺序稳定，便于复现和排查。
        for path in sorted(config.data_dir.rglob("*")):
            # 跳过目录等非文件、符号链接和不支持的后缀；lower() 使 .MD 等大写后缀也能识别。
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            # 例如 data/guide/install.md → guide/install.md；as_posix() 统一使用 / 分隔路径。
            # 使用相对路径，使不同机器的项目根目录不影响文档 ID。
            name = path.relative_to(config.data_dir).as_posix()
            text = path.read_text(encoding="utf-8")
            # strip() 这里只用于判断是否全为空白，不修改后续保存的原始 text。
            # 原有文档如果变为空白，将不再进入 hashes，后面会被识别为需要删除的文档。
            if not text.strip():
                continue
            # 相对路径回答“是哪份文档”，内容哈希回答“内容是否改变”；重命名视为删旧加新。
            # encode() 将文本转成 UTF-8 字节，sha256 计算摘要，hexdigest() 转成十六进制字符串。
            hashes[name] = hashlib.sha256(text.encode()).hexdigest()
            # [学习点 W2-01] 第 2 周：Document、稳定 ID 与元数据（框架能力）
            # 学习内容：text 是内容，id_ 使用相对路径，metadata.source 用于过滤与来源展示；读取文件由项目自行实现。
            # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/loading/documents_and_nodes/
            documents[name] = Document(text=text, id_=name, metadata={"source": name})

        # 4. 查找可复用的旧快照。manifest 是构建清单，其中 files 保存上次的路径与内容哈希。
        # 先用空字典兜底：首次构建或配置变化时，当前所有有效文档都会被归入 added。
        old_hashes = {}
        try:
            # current() 读取 CURRENT 指向的版本，并确认旧快照的配置指纹与本次配置一致。
            old_path, manifest = current(config)
            old_hashes = manifest["files"]
        except IndexNotReady:
            # 无旧索引或配置指纹失配时走全量重建；损坏的 JSON 等其他异常仍向外报告。
            old_path = None

        # 5. 对比新旧字典，区分新增、删除和内容修改；未变文档无需重新生成向量。
        # set(字典) 取得键的集合；A - B 表示只存在于 A 的键，& 表示两边共有的键。
        # 例如旧版 {a,b,c}、新版 {b,c,d}，且 c 内容变了：added=[d]、removed=[a]、changed=[c]。

        '''
        找出本次新增的文件，并把文件路径排序后保存到 added：
        added = sorted(set(hashes) - set(old_hashes))
        假设两个字典分别是：
        # 当前扫描得到的文件及内容哈希
        hashes = {
            "安装.md": "哈希A",
            "配置.md": "哈希B",
            "计费.md": "哈希C",
        }

        # 上一次构建记录的文件及内容哈希
        old_hashes = {
            "安装.md": "哈希A",
            "配置.md": "哈希B",
        }

        分三步理解：
        ① set(hashes)：取字典的键，转成集合
        set(hashes)
        # {"安装.md", "配置.md", "计费.md"}

        set(old_hashes)
        # {"安装.md", "配置.md"}

        注意：这里取的是文件路径，不是哈希值。

        ② -：计算集合差集
        set(hashes) - set(old_hashes)
        # {"计费.md"}

        意思是：找出“当前有、以前没有”的文件路径，也就是新增文件。
        '''
        added = sorted(set(hashes) - set(old_hashes))
        removed = sorted(set(old_hashes) - set(hashes))
        changed = sorted(k for k in hashes.keys() & old_hashes.keys() if hashes[k] != old_hashes[k])
        # 必须已有可用旧快照，且三个列表都为空，才可跳过构建；不创建新版本，也不切换 CURRENT。
        # len(hashes) 是有效源文档数，不是切分后的 Node 数；即使这里 return，锁也会被释放。

        # 如果有可复用的旧索引，而且文档没有新增、删除或修改，就跳过构建。
        if old_path and not (added or removed or changed):
            return {"status": "unchanged", "documents": len(hashes), "added": [], "changed": [], "removed": []}

        # 6. 准备分块器与向量模型。Document 是整份文档，Node 是随后独立存储和检索的片段。
        # [学习点 W2-02] 第 2 周：分块与重叠（框架能力）
        # 学习内容：SentenceSplitter 把 Document 转为 Node；chunk_size 与 chunk_overlap 以 tokenizer 的 token 数计。
        # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/loading/node_parsers/modules/
        # 重叠缓解答案跨边界被拆散的问题，但会增加向量数量和重复上下文。
        # token 不是字符数；框架还会为元数据预留空间，实际正文块可能小于 chunk_size。
        splitter = SentenceSplitter(chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
        # 根据 mode 选择 demo 哈希向量或 Ollama Embedding；这里不调用用于生成回答的 LLM。
        embed = embedding(config)

        # 7A. 有兼容的旧快照：加载到内存后增量更新，保留未变化文档的节点和向量。
        if old_path:
            # StorageContext 恢复文档存储、向量存储等组件；load_index_from_storage 恢复索引对象。
            # 显式传入 embed，确保后续新增节点使用与旧索引兼容的向量模型。
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(old_path)), embed_model=embed)
            # [学习点 W3-04] 第 3 周：增量维护（框架 API／项目编排）
            # 学习内容：delete_ref_doc 删除原文档关联节点，insert_nodes 插入更新节点；文件哈希和变更集合由项目维护。
            # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/indexing/document_management/
            # 先删除修改文档的全部旧节点，再插入新节点，避免旧版本事实残留在检索结果中。

            #  这里的 removed、changed 都是文件相对路径组成的列表，name 是循环时依次取出的一个路径。
            for name in removed + changed:
                # name 对应 Document.id_；按原文档关联关系删除其节点，并同步清理 docstore。
                index.delete_ref_doc(name, delete_from_docstore=True)
            if added or changed:
                # 列表推导式取出新增和修改的 Document；切分后只为这些 Node 计算并插入向量。
                nodes = splitter.get_nodes_from_documents([documents[k] for k in added + changed])
                index.insert_nodes(nodes)
            # 如果本次只有删除，不必插入节点；若文档全部删除，也会保存空索引以清除旧内容。
        else:
            # 7B. 首次构建或配置不兼容：将当前全部 Document 切分，创建全新的向量索引。
            # documents.values() 取得字典中的文档对象，list() 将它们转成框架所需的列表。
            nodes = splitter.get_nodes_from_documents(list(documents.values()))
            # [学习点 W1-05] 第 1 周：Node 到向量索引（框架能力）
            # 学习内容：VectorStoreIndex 为 Node 生成向量并组织存储；这里使用默认本地存储，不依赖外部向量数据库。
            # 文档来源：https://docs.llamaindex.org.cn/en/stable/getting_started/starter_example/
            index = VectorStoreIndex(nodes, embed_model=embed)

        # 8. 把更新后的完整索引保存到新版本目录，不直接覆盖旧目录。
        # [学习点 W3-05] 第 3 周：持久化与快照发布（框架 API／项目工程实现）
        # 学习内容：persist 是框架 API；版本目录和 CURRENT 原子替换是项目策略，确保失败构建不覆盖旧快照。
        # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/storing/save_load/
        # 先完整写入新快照，再切换指针。构建失败不会破坏可用的旧快照。
        # UUID 的 hex 形式生成随机版本名，例如 .storage/7e.../，避免重复构建使用相同目录。
        version = uuid.uuid4().hex
        target = config.storage_dir / version
        # persist 保存索引结构、文档存储和向量存储；“增量更新”不代表这里仅写入增量文件。
        index.storage_context.persist(persist_dir=str(target))
        # manifest.json 记录配置指纹与本次全部文档哈希，供下次校验与变更比较。
        # ensure_ascii=False 保留可读的中文路径；indent=2 使用两空格缩进，方便人工查看。
        (target / "manifest.json").write_text(json.dumps({"config": fingerprint(config), "files": hashes}, ensure_ascii=False, indent=2))

        # 9. 发布新版本：CURRENT 只保存版本目录名，不保存索引内容。
        # 先写临时指针，避免读者在写入过程中看到空指针或尚未写完的版本名。
        pending = config.storage_dir / "CURRENT.tmp"
        pending.write_text(version)
        # 同一文件系统的原子替换让读者看到旧指针或新指针；这不等于断电持久性保证（未 fsync）。
        # 此策略依赖本地独立快照，不能直接用于会立即修改共享数据的远程向量数据库。
        os.replace(pending, config.storage_dir / "CURRENT")

        # 10. 返回构建摘要，CLI 会将其显示为 JSON；随后退出 with 并释放锁。
        # added/changed/removed 是相对于可复用旧快照的变化；全量重建时当前文档均计入 added。
        # 历史目录不会在这里删除；发布前失败也可能留下未被 CURRENT 引用的目录。
        return {"status": "built", "documents": len(hashes), "added": added, "changed": changed, "removed": removed}
