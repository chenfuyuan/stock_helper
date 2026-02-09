from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from src.shared.infrastructure.db.base import Base

class LLMConfigModel(Base):
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String, unique=True, index=True, nullable=False)
    vendor = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    base_url = Column(String, nullable=True)
    model_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=1)
    tags = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_entity(self):
        from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
        return LLMConfig(
            id=self.id,
            alias=self.alias,
            vendor=self.vendor,
            provider_type=self.provider_type,
            api_key=self.api_key,
            base_url=self.base_url,
            model_name=self.model_name,
            description=self.description,
            priority=self.priority,
            tags=self.tags or [],
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    def __repr__(self):
        return f"<LLMConfigModel(alias={self.alias}, model={self.model_name}, id={self.id})>"
    
    @staticmethod
    def from_entity(entity):
        return LLMConfigModel(
            id=entity.id,
            alias=entity.alias,
            vendor=entity.vendor,
            provider_type=entity.provider_type,
            api_key=entity.api_key,
            base_url=entity.base_url,
            model_name=entity.model_name,
            description=entity.description,
            priority=entity.priority,
            tags=entity.tags,
            is_active=entity.is_active
        )
