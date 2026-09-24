import json
import time
from .indexing import load_index
from .retrieval import retrieve


# [学习点 W4-01] 第 4 周：检索评估与粒度（概念参考／自行实现）
# 学习内容：手算文档级 Hit Rate、Recall@k、MRR；参考官方评估思路，但未调用 RetrieverEvaluator。
# 文档来源：https://docs.llamaindex.org.cn/en/stable/examples/evaluation/retrieval/retriever_eval/
def evaluate(config, path):
    # 1. 读取题库。每题至少提供 question 和 expected_sources；reference_answer
    # 留给人工检查回答质量，本函数只评估检索，既不读取它也不调用 LLM 判分。
    cases = json.loads(path.read_text())
    if not cases:
        raise ValueError("评估集不能为空")
    # 所有题共用同一个已构建索引；load_index 会检查 Embedding/分块配置是否匹配。
    # manifest 在此不参与计算，所以用 _ 明确表示忽略它。
    index, _ = load_index(config)
    # rows 保存逐题结果，最后既用于计算汇总指标，也会原样放进报告。
    rows = []
    for case in cases:
        # 2. 逐题检索。计时从 retrieve 前开始，不包含上面的索引加载，也不包含回答生成。
        start = time.perf_counter()
        results = retrieve(index, case["question"], config)
        # top_k 截断的是片段列表：来源可重复。Recall 按来源去重，首次命中的排名仍按片段计算。
        # actual 实际检索到的来源 保留检索顺序，例如 ["A.md", "A.md", "B.md"] 代表三个 Node 来自两份文件。
        actual = [n.node.metadata["source"] for n in results]
        # expected_sources 是人工标注的相关来源；集合去重后方便判断命中并计算交集。
        # 空集合表示无答案题，不能把它的 Recall 当作 0，因为分母为 0。

        # 期待检索到的来源
        expected = set(case["expected_sources"])
        # 例：期望 {A,B}，召回 [C,A,A]，则 hit=1、recall=1/2、rr=1/2。
        # enumerate(..., 1) 从排名 1 开始；next 找首个相关片段，没有则返回 None。
        # 同一文件多个片段仍各占一个排名位置；这里不是对唯一文件重新排序。
        first = next((i for i,s in enumerate(actual, 1) if s in expected), None)

        # 3. 记录本题指标：
        # hit：前 top_k 个片段中至少一个来自期望来源；有答案但未命中为 False。
        # recall：命中的不同期望来源数 / 期望来源总数；用 集合set(actual) 避免同一来源重复计数。
        # rr：首个相关片段排名的倒数，例如第 2 位命中为 1/2，未命中为 0。
        # 无答案题的 hit/recall 为 None，rr 为 0；下方汇总会跳过整道无答案题。
        # seconds 只覆盖本题检索和上述计算，不能解读为模型生成或完整请求耗时。

        """
        召回率：
        "recall": len(expected & set(actual)) / len(expected) if expected else None

        假设：
        expected = {"安装.md", "配置.md"}   # 这题需要找到的来源
        actual = ["配置.md", "配置.md", "计费.md"]  # 实际检索到的片段来源

        逐步计算：
        set(actual)
        # {"配置.md", "计费.md"}：去掉重复来源
        expected & set(actual)
        # {"配置.md"}：取交集，也就是成功找到的期望来源
        len(expected & set(actual)) / len(expected)
        # 1 / 2 = 0.5
        """
        rows.append({"question": case["question"], "expected": sorted(expected), "actual": actual,
                     "hit": bool(first) if expected else None,
                     "recall": len(expected & set(actual))/len(expected) if expected else None,
                     "rr": 1/first if first else 0,
                     "seconds": round(time.perf_counter()-start, 4)})
    # [学习点 W4-02] 第 4 周：检索评估与回答评估的边界（评估设计）
    # 学习内容：无答案题不计入召回分母；本脚本不判回答正确性、忠实性或拒答质量，需另行评估。
    # 文档来源：https://docs.llamaindex.org.cn/en/stable/module_guides/evaluating/
    # 4. 只汇总有标注来源的题；无答案题需另外评估是否正确拒答。
    answerable = [r for r in rows if r["expected"]]
    # 对有答案的问题逐题等权平均（宏平均）；MRR 关注首个相关结果，不衡量全部证据是否齐全。
    count = len(answerable)
    # 5. 返回实验配置、汇总值和逐题详情，便于对比不同检索方式或 top_k。
    # 如果题库全为无答案题，平均指标返回 None，避免除零并表示“此指标不适用”。
    # metric_level 明确标记相关性按源文件判断，而不是按具体 Node 的答案片段判断。

    """
    hit_rate命中率：有多少比例的题，在前 top_k 个片段中至少出现一个期望来源。每题命中记 1，否则记 0，再求平均。
    recall_at_k 平均召回率：每题计算“找到了几个不同的期望来源 ÷ 期望来源总数”，再对题目求平均。同一文件返回多个片段只算找到一个来源。
    mrr平均倒数排名：每题找到首个相关片段的排名 rank，记 1/rank；没找到记 0，再求平均。越早出现相关结果，分数越高。
    """

    return {"mode": config.mode, "retrieval": config.retrieval, "top_k": config.top_k,
            "metric_level": "source_document", "answerable_count": count,
            "hit_rate": sum(r["hit"] for r in answerable)/count if count else None,
            "recall_at_k": sum(r["recall"] for r in answerable)/count if count else None,
            "mrr": sum(r["rr"] for r in answerable)/count if count else None,
            "note": "仅为文档级检索指标；无答案题不计入召回指标，回答正确性和拒答需另行人工评估。",
            "cases": rows}
