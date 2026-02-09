from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.db.session import get_db_session
from src.modules.llm_platform.infrastructure.persistence.repositories.pg_config_repo import PgLLMConfigRepository
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.modules.llm_platform.application.services.config_service import ConfigService
from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.exceptions import ConfigNotFoundException, DuplicateConfigException

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
    
    class Config:
        from_attributes = True

# Dependency
def get_config_service(db: AsyncSession = Depends(get_db_session)) -> ConfigService:
    repo = PgLLMConfigRepository(db)
    registry = LLMRegistry()
    registry.set_repository(repo) # Ensure repo is set
    return ConfigService(repo, registry)

@router.get("", response_model=List[LLMConfigResponse])
async def get_configs(service: ConfigService = Depends(get_config_service)):
    return await service.get_all_configs()

@router.get("/{alias}", response_model=LLMConfigResponse)
async def get_config(
    alias: str, 
    service: ConfigService = Depends(get_config_service)
):
    try:
        return await service.get_config(alias)
    except ConfigNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    dto: LLMConfigCreate, 
    service: ConfigService = Depends(get_config_service)
):
    entity = LLMConfig(**dto.dict())
    try:
        return await service.create_config(entity)
    except DuplicateConfigException as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.patch("/{alias}", response_model=LLMConfigResponse)
async def update_config(
    alias: str, 
    dto: LLMConfigUpdate, 
    service: ConfigService = Depends(get_config_service)
):
    try:
        return await service.update_config(alias, dto.dict(exclude_unset=True))
    except ConfigNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{alias}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    alias: str, 
    service: ConfigService = Depends(get_config_service)
):
    try:
        await service.delete_config(alias)
    except ConfigNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/refresh")
async def refresh_registry(service: ConfigService = Depends(get_config_service)):
    await service.refresh_registry()
    return {"status": "refreshed"}
