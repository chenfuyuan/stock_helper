"""
概念关系扩展信息校验 DTO。

用于校验存储在 concept_relation.ext_info（JSONB 字段）中的追溯上下文数据。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ManualExtInfo(BaseModel):
    """
    手动创建关系的扩展信息模型。
    
    用于校验手动创建关系时 ext_info 字段的结构。
    """

    note: str | None = Field(default=None, description="用户备注说明")
    reason: str | None = Field(default=None, description="建立关系的理由")


class LLMExtInfo(BaseModel):
    """
    LLM 推荐关系的扩展信息模型。
    
    用于校验 LLM 推荐关系时 ext_info 字段的结构，确保完整追溯信息。
    """

    model: str = Field(description="LLM 模型名称")
    model_version: str | None = Field(default=None, description="模型版本")
    prompt: str = Field(description="完整输入 prompt")
    raw_output: str = Field(description="LLM 原始输出")
    parsed_result: dict = Field(description="解析后的分析结果")
    reasoning: str = Field(description="推理依据")
    batch_id: str | None = Field(default=None, description="批次 ID（用于批量分析追溯）")
    analyzed_at: datetime = Field(description="分析时间")

    class Config:
        """Pydantic 配置。"""

        json_encoders = {datetime: lambda v: v.isoformat()}
