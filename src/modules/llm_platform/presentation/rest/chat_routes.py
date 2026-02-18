from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.modules.llm_platform.application.services.llm_service import (
    LLMService,
)
from src.shared.dtos import BaseResponse

router = APIRouter(prefix="/llm-platform/chat", tags=["LLM Platform"])


# DTOs
class ChatRequest(BaseModel):
    """
    聊天生成请求 DTO
    """

    prompt: str = Field(..., description="用户输入的提示词")
    system_message: Optional[str] = Field(None, description="系统预设消息")
    alias: Optional[str] = Field(None, description="指定使用的大模型别名")
    tags: Optional[List[str]] = Field(None, description="通过标签筛选大模型")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="采样温度")


class ChatResponse(BaseModel):
    """
    聊天生成响应 DTO
    """

    response: str = Field(..., description="大模型生成的文本")
    # 由于 LLMService.generate 目前只返回字符串，我们暂时无法返回实际使用的模型别名
    # 如果需要，后续可以修改 Service 层返回更详细的信息


# Dependency
def get_llm_service() -> LLMService:
    return LLMService()


@router.post("/generate", response_model=BaseResponse[ChatResponse])
async def generate_text(request: ChatRequest, service: LLMService = Depends(get_llm_service)):
    """
    调用大模型生成文本接口。

    功能描述：
    接收用户的 prompt 和配置参数，路由到合适的 LLM Provider 进行文本生成。

    参数:
    - request: ChatRequest 请求体，包含 prompt, alias, tags 等。

    返回:
    - ChatResponse: 包含生成的文本。

    异常:
    - 500: 内部服务错误（如无可用模型、API 调用失败）。
    """
    logger.info(f"API: generate_text called. Alias={request.alias}, Tags={request.tags}")
    try:
        result = await service.generate(
            prompt=request.prompt,
            system_message=request.system_message,
            temperature=request.temperature,
            alias=request.alias,
            tags=request.tags,
        )
        logger.info("API: generate_text completed successfully")
        return BaseResponse(
            success=True,
            code="LLM_CHAT_SUCCESS",
            message="LLM 对话成功完成",
            data=ChatResponse(response=result)
        )
    except Exception as e:
        logger.error(f"API: generate_text failed: {str(e)}")
        # 捕获可能的路由错误或调用错误
        raise HTTPException(status_code=500, detail=str(e))
