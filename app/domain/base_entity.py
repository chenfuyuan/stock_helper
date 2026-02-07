import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """
    领域实体基类
    包含所有实体共有的基础字段：ID、创建时间、更新时间
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # 允许从 ORM 模型直接创建 Pydantic 模型
        orm_mode = True
