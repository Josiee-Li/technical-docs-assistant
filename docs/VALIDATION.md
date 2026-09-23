# 验证记录

验证环境：macOS ARM64、Python 3.12.13、llama-index-core 0.14.25。完整依赖解析见 uv.lock。

## 已运行

- 项目作为 editable package 安装成功，CLI 入口可用。
- `uv sync --locked --extra dev` 与锁文件一致。
- `pytest -q`：16 项通过，0 项失败。
- 实际运行 ingest、ask、eval、workflow 命令成功。
- FastAPI 查询与流式接口通过 TestClient 验证。
- 真正的 LlamaIndex FunctionAgent 使用脚本化 Ollama 替身完成检索工具和计算工具调用；这验证框架接口，不代表真实模型工具选择质量。
- Workflow 替身测试验证：证据不足时最多重试一次，保留原始问题。

## 示例评估

`reports/baseline.json` 包含 14 道题，其中 12 道有答案。
当前 demo + hybrid + top_k=4 的文档级 Hit Rate、Recall@k 和 MRR 均为 1.0。

只有 5 份小文档且题目直接围绕示例设计，因此这个结果只是流程基线，不能说明真实语义检索或回答质量。2 道无答案题仍返回候选片段，正好用于后续拒答实验；它们没有计入召回指标。

`reports/workflow-demo.json` 展示检索结果与工作流 trace。demo 的证据判断仅检查是否有片段。

## 未执行

- 未安装或下载 Ollama 模型，未实测真实生成、真实模型工具调用或模型判断准确性。
- 未安装可选 CrossEncoder 模型，未实测其排序效果与资源使用。
- 未进行大语料、并发负载和 Windows/Linux 实机测试。

## 依赖提示

测试时出现 Starlette 对 httpx 测试客户端的弃用提示，以及依赖内部反射触发的 Pydantic 弃用提示，共 93 条 warning，没有测试失败。没有隐藏这些提示；后续升级依赖时需要重新运行测试。

## 学习标注检查

新增 33 个代码学习标注及 CODE_MAP.md，覆盖第 1～8 周。与上一版压缩包比较，11 个 Python 文件的 AST（包含 docstring）完全一致；本次仅修改注释和文档，没有重复运行功能测试。学习编号唯一，代码与对照表的本地链接均已检查。
