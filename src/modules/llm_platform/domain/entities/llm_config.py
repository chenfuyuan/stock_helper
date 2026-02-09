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

    def __repr__(self):
        masked_key = "******"
        if self.api_key and len(self.api_key) >= 8:
            masked_key = f"{self.api_key[:3]}...{self.api_key[-4:]}"
        
        return (
            f"LLMConfig(alias={self.alias}, vendor={self.vendor}, "
            f"model={self.model_name}, api_key={masked_key}, "
            f"priority={self.priority}, active={self.is_active})"
        )
