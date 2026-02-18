from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.application.services.config_service import (
    ConfigService,
)
from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.exceptions import (
    ConfigNotFoundException,
    DuplicateConfigException,
)
from src.modules.llm_platform.infrastructure.persistence.repositories.pg_config_repo import (
    PgLLMConfigRepository,
)
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.shared.infrastructure.db.session import get_db_session
from src.shared.dtos import BaseResponse

router = APIRouter(prefix="/llm-platform/configs", tags=["LLM Platform"])


# DTOs
class LLMConfigBase(BaseModel):
    alias: str
    vendor: str
    provider_type: str
    api_key: str
    base_url: Optional[str] = None
    model_name: str
    description: Optional[str] = None
    priority: int = 1
    tags: List[str] = []
    is_active: bool = True


class LLMConfigCreate(LLMConfigBase):
    pass


class LLMConfigUpdate(BaseModel):
    vendor: Optional[str] = None
    provider_type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class LLMConfigResponse(LLMConfigBase):
    id: int

    @validator("api_key", always=True)
    def mask_api_key(cls, v):
        if not v or len(v) < 8:
            return "******"
        return f"{v[:3]}...{v[-4:]}"

    class Config:
        from_attributes = True


# Dependency
def get_config_service(
    db: AsyncSession = Depends(get_db_session),
) -> ConfigService:
    repo = PgLLMConfigRepository(db)
    registry = LLMRegistry()
    registry.set_repository(repo)  # Ensure repo is set
    return ConfigService(repo, registry)


@router.get("", response_model=BaseResponse[List[LLMConfigResponse]])
async def get_configs(service: ConfigService = Depends(get_config_service)):
    """
    获取所有大模型配置。
    """
    logger.info("API: get_configs called")
    configs = await service.get_all_configs()
    return BaseResponse(
        success=True,
        code="CONFIG_LIST_SUCCESS",
        message="大模型配置列表获取成功",
        data=configs
    )


@router.get("/{alias}", response_model=BaseResponse[LLMConfigResponse])
async def get_config(alias: str, service: ConfigService = Depends(get_config_service)):
    """
    根据别名获取大模型配置详情。
    """
    logger.info(f"API: get_config called with alias={alias}")
    try:
        config = await service.get_config(alias)
        return BaseResponse(
            success=True,
            code="CONFIG_DETAIL_SUCCESS",
            message="大模型配置详情获取成功",
            data=config
        )
    except ConfigNotFoundException as e:
        logger.warning(f"API: Config not found: {alias}")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=BaseResponse[LLMConfigResponse], status_code=status.HTTP_201_CREATED)
async def create_config(dto: LLMConfigCreate, service: ConfigService = Depends(get_config_service)):
    """
    创建新的大模型配置。
    """
    logger.info(f"API: create_config called with alias={dto.alias}")
    entity = LLMConfig(**dto.dict())
    try:
        result = await service.create_config(entity)
        logger.info(f"API: Config created successfully: {dto.alias}")
        return BaseResponse(
            success=True,
            code="CONFIG_CREATE_SUCCESS",
            message="大模型配置创建成功",
            data=result
        )
    except DuplicateConfigException as e:
        logger.warning(f"API: Duplicate config: {dto.alias}")
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{alias}", response_model=BaseResponse[LLMConfigResponse])
async def update_config(
    alias: str,
    dto: LLMConfigUpdate,
    service: ConfigService = Depends(get_config_service),
):
    """
    更新现有的大模型配置。
    """
    logger.info(f"API: update_config called with alias={alias}")
    try:
        result = await service.update_config(alias, dto.dict(exclude_unset=True))
        logger.info(f"API: Config updated successfully: {alias}")
        return BaseResponse(
            success=True,
            code="CONFIG_UPDATE_SUCCESS",
            message="大模型配置更新成功",
            data=result
        )
    except ConfigNotFoundException as e:
        logger.warning(f"API: Config not found for update: {alias}")
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{alias}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(alias: str, service: ConfigService = Depends(get_config_service)):
    """
    删除大模型配置。
    """
    logger.info(f"API: delete_config called with alias={alias}")
    try:
        await service.delete_config(alias)
        logger.info(f"API: Config deleted successfully: {alias}")
    except ConfigNotFoundException as e:
        logger.warning(f"API: Config not found for deletion: {alias}")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/refresh", response_model=BaseResponse[dict])
async def refresh_registry(
    service: ConfigService = Depends(get_config_service),
):
    """
    手动刷新大模型注册表。
    """
    logger.info("API: refresh_registry called")
    await service.refresh_registry()
    return BaseResponse(
        success=True,
        code="REGISTRY_REFRESH_SUCCESS",
        message="大模型注册表刷新成功",
        data={"status": "refreshed"}
    )
