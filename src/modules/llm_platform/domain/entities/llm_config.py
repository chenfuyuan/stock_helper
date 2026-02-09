from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class LLMConfig:
    alias: str
    vendor: str
    provider_type: str
    api_key: str
    model_name: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    priority: int = 1
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
