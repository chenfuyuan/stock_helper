"""
执行上下文：基于 contextvars 在请求/流水线内隐式传递 session_id。

Coordinator 在编排入口设置 ExecutionContext，下游（LLM 调用、外部 API 适配器）
通过 current_execution_ctx.get() 读取，无需在 Port 签名中传递 session_id。
"""

import contextvars

from pydantic import BaseModel


class ExecutionContext(BaseModel):
    """当前执行上下文，用于关联审计日志与会话。"""

    session_id: str


# 默认 None：无研究流水线上下文时（如单测、定时任务）仍可正常调用 LLM/API，只是不关联 session
current_execution_ctx: contextvars.ContextVar[ExecutionContext | None] = contextvars.ContextVar(
    "current_execution_ctx", default=None
)
