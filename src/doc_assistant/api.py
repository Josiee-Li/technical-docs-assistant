from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .config import Config
from .indexing import IndexNotReady
from .service import Assistant


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


# [学习点 W8-01] 第 8 周：请求模型与边界校验（第三方 Web 框架）
# 学习内容：FastAPI 使用 Pydantic 模型校验问题长度和会话历史；这属于应用层，不是 LlamaIndex 功能。
# 文档来源：https://fastapi.tiangolo.com/tutorial/body/
class Query(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # 每个请求独立创建列表；会话由调用方传入，服务端不保存聊天历史。
    history: list[Message] = Field(default_factory=list, max_length=6)
    source: str | None = Field(default=None, max_length=500)


def create_app(config=None):
    app = FastAPI(title="LlamaIndex 技术文档助手", version="0.1.0")
    assistant = Assistant(config or Config.from_env())

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": assistant.config.mode}

    @app.post("/query")
    def query(body: Query):
        try:
            return assistant.query(body.question, [m.model_dump() for m in body.history], body.source).to_dict()
        # 子类异常须先捕获：IndexNotReady 继承 ValueError，索引状态冲突对应 409。
        except IndexNotReady as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        except Exception as error:
            import logging
            logging.getLogger(__name__).exception("查询失败")
            raise HTTPException(503, "查询失败，请检查模型服务和服务端日志") from error

    # [学习点 W8-02] 第 8 周：流式 HTTP 响应（第三方 Web 框架）
    # 学习内容：StreamingResponse 将 service 的事件迭代器转为逐行 JSON；检索前置错误仍可返回 HTTP 状态码。
    # 文档来源：https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    @app.post("/query/stream")
    def stream(body: Query):
        import json
        from fastapi.responses import StreamingResponse
        try:
            events = assistant.stream(body.question, [m.model_dump() for m in body.history], body.source)
        # 子类异常须先捕获：IndexNotReady 继承 ValueError，索引状态冲突对应 409。
        except IndexNotReady as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        except Exception as error:
            import logging
            logging.getLogger(__name__).exception("流式检索失败")
            raise HTTPException(503, "检索失败，请检查服务端日志") from error
        # NDJSON 用换行划分事件；网络分片不保证一片一行，客户端须缓冲后按行解析。
        return StreamingResponse((json.dumps(event, ensure_ascii=False) + "\n" for event in events),
                                 media_type="application/x-ndjson")

    return app


app = create_app()
