from typing import List, Optional

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.ports.repositories.config_repo import (
    ILLMConfigRepository,
)
from src.modules.llm_platform.infrastructure.persistence.models.llm_config_model import (
    LLMConfigModel,
)


class PgLLMConfigRepository(ILLMConfigRepository):
    """
    PostgreSQL 实现的 LLM 配置仓储
    """

    def __init__(self, session: AsyncSession):
        """
        初始化仓储

        Args:
            session (AsyncSession): SQLAlchemy 异步会话
        """
        self.session = session

    async def get_all(self) -> List[LLMConfig]:
        """
        获取所有 LLM 配置
        """
        try:
            stmt = select(LLMConfigModel)
            result = await self.session.execute(stmt)
            return [model.to_entity() for model in result.scalars().all()]
        except Exception as e:
            logger.error(f"DB Error in get_all: {str(e)}")
            raise e

    async def get_active_configs(self) -> List[LLMConfig]:
        """
        获取所有激活的 LLM 配置
        """
        try:
            stmt = select(LLMConfigModel).where(LLMConfigModel.is_active.is_(True))
            result = await self.session.execute(stmt)
            return [model.to_entity() for model in result.scalars().all()]
        except Exception as e:
            logger.error(f"DB Error in get_active_configs: {str(e)}")
            raise e

    async def get_by_alias(self, alias: str) -> Optional[LLMConfig]:
        """
        根据别名获取配置
        """
        try:
            stmt = select(LLMConfigModel).where(LLMConfigModel.alias == alias)
            result = await self.session.execute(stmt)
            model = result.scalars().first()
            return model.to_entity() if model else None
        except Exception as e:
            logger.error(f"DB Error in get_by_alias({alias}): {str(e)}")
            raise e

    async def save(self, config: LLMConfig) -> LLMConfig:
        """
        保存或更新配置 (Upsert)
        """
        try:
            data = {
                "alias": config.alias,
                "vendor": config.vendor,
                "provider_type": config.provider_type,
                "api_key": config.api_key,
                "base_url": config.base_url,
                "model_name": config.model_name,
                "description": config.description,
                "priority": config.priority,
                "tags": config.tags,
                "is_active": config.is_active,
            }

            # Use upsert (insert on conflict update)
            stmt = insert(LLMConfigModel).values(**data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["alias"],
                set_={
                    "vendor": stmt.excluded.vendor,
                    "provider_type": stmt.excluded.provider_type,
                    "api_key": stmt.excluded.api_key,
                    "base_url": stmt.excluded.base_url,
                    "model_name": stmt.excluded.model_name,
                    "description": stmt.excluded.description,
                    "priority": stmt.excluded.priority,
                    "tags": stmt.excluded.tags,
                    "is_active": stmt.excluded.is_active,
                    "updated_at": func.now(),
                },
            ).returning(LLMConfigModel)

            result = await self.session.execute(stmt)
            model = result.scalars().first()
            await self.session.commit()
            return model.to_entity()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"DB Error in save({config.alias}): {str(e)}")
            raise e

    async def delete_by_alias(self, alias: str) -> bool:
        """
        根据别名删除配置
        """
        try:
            stmt = delete(LLMConfigModel).where(LLMConfigModel.alias == alias)
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"DB Error in delete_by_alias({alias}): {str(e)}")
            raise e
