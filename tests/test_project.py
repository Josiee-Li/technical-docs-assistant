import json
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from doc_assistant.config import Config
from doc_assistant.indexing import IndexNotReady, ingest, load_index
from doc_assistant.retrieval import retrieve
from doc_assistant.service import Assistant
from doc_assistant.evaluation import evaluate
from doc_assistant.api import create_app


# [学习点 W8-04] 第 8 周：隔离测试与回归验证（测试工程）
# 学习内容：tmp_path 为每个测试隔离语料和索引；覆盖更新、删除、失败恢复、API 与工作流，避免改动真实数据。
# 文档来源：https://docs.pytest.org/en/stable/how-to/tmp_path.html
@pytest.fixture
def config(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "network.md").write_text("连接参数 connect_timeout 默认值是 10 秒。")
    (data / "billing.md").write_text("计费规则 price：每 1000 次请求收费 2 元。")
    return Config(data_dir=data, storage_dir=tmp_path / "storage", retrieval="bm25", top_k=2)


def test_update_delete_and_noop(config):
    assert ingest(config)["documents"] == 2
    original = (config.storage_dir / "CURRENT").read_text()
    assert ingest(config)["status"] == "unchanged"
    assert (config.storage_dir / "CURRENT").read_text() == original
    (config.data_dir / "network.md").write_text("连接参数 connect_timeout 默认值是 99 秒。")
    (config.data_dir / "billing.md").unlink()
    result = ingest(config)
    assert result["changed"] == ["network.md"]
    assert result["removed"] == ["billing.md"]
    answer = Assistant(config).query("connect_timeout")
    assert len(answer.sources) == 1
    assert "99" in answer.sources[0]["text"]
    assert "10 秒" not in answer.sources[0]["text"]
    assert Assistant(config).query("price").sources == []


@pytest.mark.parametrize("method", ["dense", "bm25", "hybrid"])
def test_retrieval_and_metadata_filter(config, method):
    ingest(config)
    index, _ = load_index(config)
    results = retrieve(index, "connect_timeout", replace(config, retrieval=method))
    assert results[0].node.metadata["source"] == "network.md"
    assert retrieve(index, "connect_timeout", replace(config, retrieval=method), source="missing.md") == []
    filtered = retrieve(index, "price", replace(config, retrieval=method), source="billing.md")
    assert all(n.node.metadata["source"] == "billing.md" for n in filtered)


def test_config_change_requires_reindex(config):
    ingest(config)
    changed = replace(config, chunk_size=300)
    with pytest.raises(IndexNotReady):
        load_index(changed)
    ingest(changed)
    load_index(changed)


def test_failed_build_preserves_snapshot(config, monkeypatch):
    ingest(config)
    original = (config.storage_dir / "CURRENT").read_text()
    (config.data_dir / "network.md").write_text("changed content")
    from llama_index.core import StorageContext
    def fail(*args, **kwargs):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(StorageContext, "persist", fail)
    with pytest.raises(OSError):
        ingest(config)
    assert (config.storage_dir / "CURRENT").read_text() == original
    assert "10 秒" in Assistant(config).query("connect_timeout").sources[0]["text"]
    assert not (config.storage_dir / "build.lock").exists()


def test_empty_corpus_and_lock(config):
    ingest(config)
    for file in config.data_dir.iterdir():
        file.unlink()
    ingest(config)
    assert Assistant(config).query("anything").sources == []
    lock = config.storage_dir / "build.lock"
    lock.write_text("123")
    with pytest.raises(ValueError, match="构建"):
        ingest(config)


def test_evaluation(config, tmp_path):
    ingest(config)
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([
        {"question": "connect_timeout", "expected_sources": ["network.md"]},
        {"question": "unknown", "expected_sources": []},
    ]))
    report = evaluate(config, cases)
    assert report["hit_rate"] == 1
    assert report["mrr"] == 1
    assert report["answerable_count"] == 1
    assert report["cases"][1]["hit"] is None


def test_api(config):
    client = TestClient(create_app(config))
    assert client.get("/health").json()["mode"] == "demo"
    assert client.post("/query", json={"question": "test"}).status_code == 409
    ingest(config)
    response = client.post("/query", json={"question": "connect_timeout"})
    assert response.status_code == 200
    assert response.json()["sources"][0]["source"] == "network.md"
    assert "离线演示" in response.json()["answer"]
    assert client.post("/query", json={"question": ""}).status_code == 422
    assert client.post("/query", json={"question": "x", "history": [{"role":"system","content":"x"}]}).status_code == 422


def test_demo_chat(config):
    ingest(config)
    response = Assistant(config).query("默认值呢？", [{"role":"user", "content":"connect_timeout"}])
    assert "connect_timeout" in response.search_query
    assert response.sources[0]["source"] == "network.md"


def test_calculator():
    from doc_assistant.advanced import calculate
    assert calculate("2500 / 1000 * 2") == 5
    assert calculate("-(3 + 2) * 4") == -20
    for expression in ["__import__('os').system('id')", "2**10000", "1/0", "True", "1e999"]:
        with pytest.raises(ValueError):
            calculate(expression)


def test_workflow(config):
    import asyncio
    from doc_assistant.advanced import run_workflow
    ingest(config)
    answer = asyncio.run(run_workflow(config, "connect_timeout"))
    assert answer["trace"][0]["step"] == "search"
    assert answer["result"]["sources"][0]["source"] == "network.md"
    assert answer["trace"][-1]["method"] == "nonempty_only"


def test_stream(config):
    ingest(config)
    client = TestClient(create_app(config))
    response = client.post("/query/stream", json={"question": "connect_timeout"})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [event["type"] for event in events] == ["sources", "delta", "done"]
    assert events[0]["sources"][0]["source"] == "network.md"


def test_real_generation_contract(config, monkeypatch):
    from types import SimpleNamespace
    from doc_assistant import service
    class FakeLLM:
        def complete(self, prompt):
            if "改写" in prompt:
                return "connect_timeout 默认值"
            assert "[1]" in prompt and "10 秒" in prompt
            return "默认值是 10 秒。[1]"
        def stream_complete(self, prompt):
            yield SimpleNamespace(delta="10 秒")
            yield SimpleNamespace(delta="[1]")
    # 用离线嵌入替身验证真实生成分支，不宣称测试了实际模型。
    from doc_assistant.models import DemoEmbedding
    from doc_assistant import indexing
    monkeypatch.setattr(indexing, "embedding", lambda config: DemoEmbedding())
    monkeypatch.setattr(service, "llm", lambda config: FakeLLM())
    real = replace(config, mode="ollama")
    ingest(real)
    response = Assistant(real).query("默认值呢？", [{"role": "user", "content": "connect_timeout"}])
    assert response.answer == "默认值是 10 秒。[1]"
    assert response.search_query == "connect_timeout 默认值"
    assert [e["text"] for e in Assistant(real).stream("connect_timeout") if e["type"]=="delta"] == ["10 秒", "[1]"]


def test_workflow_retry_is_bounded(config, monkeypatch):
    import asyncio
    from doc_assistant import advanced
    from doc_assistant.service import Answer
    calls = []
    class FakeAssistant:
        def __init__(self, config):
            pass
        def query(self, query):
            calls.append(query)
            return Answer(query, query, "候选回答", [{"text": "无关证据"}], "ollama", 0)
    class Judge:
        async def acomplete(self, prompt):
            return "NO" if "YES" in prompt else "改写后的查询"
    monkeypatch.setattr(advanced, "Assistant", FakeAssistant)
    monkeypatch.setattr(advanced, "llm", lambda config: Judge())
    result = asyncio.run(advanced.run_workflow(replace(config, mode="ollama"), "原始问题"))
    assert calls == ["原始问题", "改写后的查询"]
    assert result["result"]["question"] == "原始问题"
    assert "证据不足" in result["result"]["answer"]
    assert len(result["trace"]) == 4


# [学习点 W7-06] 第 7 周：工具调用的契约测试（测试替身）
# 学习内容：保留真实 FunctionAgent 执行，替换模型输出；验证工具执行链路，不据此评价真实模型决策能力。
# 文档来源：https://docs.pytest.org/en/stable/how-to/monkeypatch.html
def test_agent_executes_tools_through_framework(config, monkeypatch):
    import asyncio
    from pydantic import PrivateAttr
    from llama_index.llms.ollama import Ollama
    from llama_index.core.base.llms.types import ChatMessage, ChatResponse, ToolCallBlock
    from doc_assistant import advanced
    ingest(config)
    class ScriptedOllama(Ollama):
        _turn: int = PrivateAttr(default=0)
        async def astream_chat_with_tools(self, **kwargs):
            self._turn += 1
            if self._turn == 1:
                blocks = [ToolCallBlock(tool_name="search_documents", tool_kwargs={"query": "price"})]
                message = ChatMessage(role="assistant", blocks=blocks)
            elif self._turn == 2:
                blocks = [ToolCallBlock(tool_name="calculator", tool_kwargs={"expression": "2500 / 1000 * 2"})]
                message = ChatMessage(role="assistant", blocks=blocks)
            else:
                message = ChatMessage(role="assistant", content="费用为 5 元，依据 billing.md。")
            async def responses():
                yield ChatResponse(message=message)
            return responses()
    fake = ScriptedOllama(model="test", context_window=4096)
    monkeypatch.setattr(advanced, "llm", lambda config: fake)
    monkeypatch.setattr(advanced, "Assistant", lambda ignored: Assistant(config))
    result = asyncio.run(advanced.run_agent(replace(config, mode="ollama"), "2500 次多少钱？"))
    assert [call["tool"] for call in result["trace"]] == ["search_documents", "calculator"]
    assert result["trace"][1]["output"] == 5
    assert "5 元" in result["answer"]
