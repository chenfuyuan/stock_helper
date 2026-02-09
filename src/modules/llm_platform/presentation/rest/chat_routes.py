from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.modules.llm_platform.application.services.llm_service import LLMService
from src.modules.llm_platform.domain.exceptions import LLMProviderException

router = APIRouter(prefix="/llm-platform/chat", tags=["LLM Platform"])

# DTOs
class ChatRequest(BaseModel):
    prompt: str = Field(..., description="用户输入的提示词")
    system_message: Optional[str] = Field(None, description="系统预设消息")
    alias: Optional[str] = Field(None, description="指定使用的大模型别名")
    tags: Optional[List[str]] = Field(None, description="通过标签筛选大模型")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="采样温度")

class ChatResponse(BaseModel):
    response: str = Field(..., description="大模型生成的文本")
    # 由于 LLMService.generate 目前只返回字符串，我们暂时无法返回实际使用的模型别名
    # 如果需要，后续可以修改 Service 层返回更详细的信息

# Dependency
def get_llm_service() -> LLMService:
    return LLMService()

@router.post("/generate", response_model=ChatResponse)
async def generate_text(
    request: ChatRequest,
    service: LLMService = Depends(get_llm_service)
):
    """
    调用大模型生成文本。
    支持通过 alias 指定模型，或通过 tags 筛选模型。
    """
    try:
        result = await service.generate(
            prompt=request.prompt,
            system_message=request.system_message,
            temperature=request.temperature,
            alias=request.alias,
            tags=request.tags
        )
        return ChatResponse(response=result)
    except Exception as e:
        # 捕获可能的路由错误或调用错误
        raise HTTPException(status_code=500, detail=str(e))
