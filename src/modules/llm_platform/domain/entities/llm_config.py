from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class LLMConfig:
    """
    大模型配置实体 (Domain Entity)
    定义了连接和使用大语言模型所需的核心属性。
    
    Attributes:
        alias (str): 配置别名，唯一标识符（如 'deepseek-v3'）。
        vendor (str): 模型厂商（如 'SiliconFlow', 'OpenAI'）。
        provider_type (str): 适配器类型（如 'openai', 'anthropic'），决定使用哪个 Provider 实现。
        api_key (str): API 密钥，敏感信息。
        model_name (str): 实际调用的模型名称（如 'deepseek-ai/DeepSeek-V3'）。
        description (Optional[str]): 配置描述信息。
        base_url (Optional[str]): API 基础地址（用于兼容 OpenAI 接口的中转服务）。
        priority (int): 优先级，数值越大优先级越高。
        tags (List[str]): 标签列表，用于通过特性筛选模型（如 ['fast', 'code']）。
        is_active (bool): 是否启用该配置。
        id (Optional[int]): 数据库主键 ID。
        created_at (Optional[datetime]): 创建时间。
        updated_at (Optional[datetime]): 更新时间。
    """
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
        """
        返回对象的字符串表示形式。
        注意：对 api_key 进行了脱敏处理，避免在日志中泄露敏感信息。
        """
        masked_key = "******"
        if self.api_key and len(self.api_key) >= 8:
            masked_key = f"{self.api_key[:3]}...{self.api_key[-4:]}"
        
        return (
            f"LLMConfig(alias={self.alias}, vendor={self.vendor}, "
            f"model={self.model_name}, api_key={masked_key}, "
            f"priority={self.priority}, active={self.is_active})"
        )
