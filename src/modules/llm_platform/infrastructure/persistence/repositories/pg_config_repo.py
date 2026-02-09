from typing import List, Optional
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.ports.repositories.config_repo import ILLMConfigRepository
from src.modules.llm_platform.infrastructure.persistence.models.llm_config_model import LLMConfigModel

class PgLLMConfigRepository(ILLMConfigRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[LLMConfig]:
        stmt = select(LLMConfigModel)
        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def get_active_configs(self) -> List[LLMConfig]:
        stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def get_by_alias(self, alias: str) -> Optional[LLMConfig]:
        stmt = select(LLMConfigModel).where(LLMConfigModel.alias == alias)
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return model.to_entity() if model else None

    async def save(self, config: LLMConfig) -> LLMConfig:
        data = {
            "alias": config.alias,
            "provider_type": config.provider_type,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model_name": config.model_name,
            "priority": config.priority,
            "tags": config.tags,
            "is_active": config.is_active,
        }
        
        # Use upsert (insert on conflict update)
        stmt = insert(LLMConfigModel).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['alias'],
            set_={
                "provider_type": stmt.excluded.provider_type,
                "api_key": stmt.excluded.api_key,
                "base_url": stmt.excluded.base_url,
                "model_name": stmt.excluded.model_name,
                "priority": stmt.excluded.priority,
                "tags": stmt.excluded.tags,
                "is_active": stmt.excluded.is_active,
                "updated_at": func.now()
            }
        ).returning(LLMConfigModel)
        
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return model.to_entity()

    async def delete_by_alias(self, alias: str) -> bool:
        stmt = delete(LLMConfigModel).where(LLMConfigModel.alias == alias)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
