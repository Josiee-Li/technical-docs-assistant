import json
import time
from .indexing import load_index
from .retrieval import retrieve


# [学习点 W4-01] 第 4 周：检索评估与粒度（概念参考／自行实现）
# 学习内容：手算文档级 Hit Rate、Recall@k、MRR；参考官方评估思路，但未调用 RetrieverEvaluator。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/examples/evaluation/retrieval/retriever_eval/
def evaluate(config, path):
    cases = json.loads(path.read_text())
    if not cases:
        raise ValueError("评估集不能为空")
    index, _ = load_index(config)
    rows = []
    for case in cases:
        start = time.perf_counter()
        results = retrieve(index, case["question"], config)
        actual = [n.node.metadata["source"] for n in results]
        expected = set(case["expected_sources"])
        first = next((i for i,s in enumerate(actual, 1) if s in expected), None)
        rows.append({"question": case["question"], "expected": sorted(expected), "actual": actual,
                     "hit": bool(first) if expected else None,
                     "recall": len(expected & set(actual))/len(expected) if expected else None,
                     "rr": 1/first if first else 0,
                     "seconds": round(time.perf_counter()-start, 4)})
    # [学习点 W4-02] 第 4 周：检索评估与回答评估的边界（评估设计）
    # 学习内容：无答案题不计入召回分母；本脚本不判回答正确性、忠实性或拒答质量，需另行评估。
    # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/evaluating/
    answerable = [r for r in rows if r["expected"]]
    count = len(answerable)
    return {"mode": config.mode, "retrieval": config.retrieval, "top_k": config.top_k,
            "metric_level": "source_document", "answerable_count": count,
            "hit_rate": sum(r["hit"] for r in answerable)/count if count else None,
            "recall_at_k": sum(r["recall"] for r in answerable)/count if count else None,
            "mrr": sum(r["rr"] for r in answerable)/count if count else None,
            "note": "仅为文档级检索指标；无答案题不计入召回指标，回答正确性和拒答需另行人工评估。",
            "cases": rows}
