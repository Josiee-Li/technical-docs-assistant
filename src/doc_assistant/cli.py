import argparse
import json
import logging
from pathlib import Path
from .config import Config
from .evaluation import evaluate
from .indexing import ingest
from .service import Assistant


# [学习点 W8-03] 第 8 周：命令行与应用分层（Python 标准库）
# 学习内容：argparse 将命令分发到索引、问答和评估模块；CLI 不承担检索算法，实现可复用的入口层。
# 文档来源：https://docs.python.org/zh-cn/3/library/argparse.html
def main():
    parser = argparse.ArgumentParser(description="LlamaIndex 技术文档学习助手")
    parser.add_argument("--mode", choices=["demo", "ollama"])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest")
    ask = commands.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--source")
    commands.add_parser("chat")
    evaluation = commands.add_parser("eval")
    evaluation.add_argument("--dataset", type=Path, default=Path("evaluation/questions.json"))
    evaluation.add_argument("--output", type=Path)
    agent = commands.add_parser("agent")
    agent.add_argument("question")
    workflow = commands.add_parser("workflow")
    workflow.add_argument("question")
    commands.add_parser("serve")
    args = parser.parse_args()
    config = Config.from_env()
    if args.mode:
        from dataclasses import replace
        config = replace(config, mode=args.mode)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        if args.command == "ingest":
            result = ingest(config)
        elif args.command == "ask":
            result = Assistant(config).query(args.question, source=args.source).to_dict()
        elif args.command == "eval":
            result = evaluate(config, args.dataset)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "chat":
            assistant, history = Assistant(config), []
            print("输入 /quit 退出；/reset 清除对话。最多保留最近三轮。")
            while True:
                question = input("你> ").strip()
                if question == "/quit":
                    break
                if question == "/reset":
                    history.clear()
                    continue
                if not question:
                    continue
                reply = assistant.query(question, history)
                print(reply.answer)
                history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": reply.answer[:1500]}])
                history = history[-6:]
            return
        elif args.command in {"agent", "workflow"}:
            import asyncio
            from .advanced import run_agent, run_workflow
            result = asyncio.run((run_agent if args.command == "agent" else run_workflow)(config, args.question))
        else:
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(config), host="127.0.0.1", port=8000)
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f"错误：{error}\n")


if __name__ == "__main__":
    main()
