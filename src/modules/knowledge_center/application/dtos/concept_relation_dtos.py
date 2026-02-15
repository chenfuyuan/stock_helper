"""
概念关系 REST API DTOs。

定义概念关系 CRUD、LLM 推荐、同步等 REST 端点的 Request / Response 数据结构。
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ===== 创建概念关系 =====
class CreateConceptRelationRequest(BaseModel):
    """创建概念关系请求 DTO。"""

    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: str = Field(
        description="关系类型（IS_UPSTREAM_OF / IS_DOWNSTREAM_OF / COMPETES_WITH / IS_PART_OF / ENABLER_FOR）"
    )
    note: str | None = Field(default=None, description="备注说明（手动创建时可选）")
    reason: str | None = Field(default=None, description="建立关系的理由（手动创建时可选）")


class ConceptRelationResponse(BaseModel):
    """概念关系响应 DTO。"""

    id: int = Field(description="关系 ID")
    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: str = Field(description="关系类型")
    source_type: str = Field(description="来源类型（MANUAL / LLM）")
    status: str = Field(description="状态（PENDING / CONFIRMED / REJECTED）")
    confidence: float = Field(description="置信度（0.0~1.0）")
    ext_info: dict = Field(description="扩展信息（追溯上下文）")
    created_by: str | None = Field(default=None, description="创建人")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


# ===== 更新概念关系 =====
class UpdateConceptRelationRequest(BaseModel):
    """更新概念关系请求 DTO。"""

    status: str | None = Field(
        default=None, description="更新状态（CONFIRMED / REJECTED）"
    )
    confidence: float | None = Field(
        default=None, description="更新置信度（可选，一般用于手动调整）"
    )


# ===== 列表查询概念关系 =====
class ListConceptRelationsRequest(BaseModel):
    """列表查询概念关系请求 DTO（Query 参数）。"""

    source_concept_code: str | None = Field(default=None, description="源概念代码筛选")
    target_concept_code: str | None = Field(default=None, description="目标概念代码筛选")
    relation_type: str | None = Field(default=None, description="关系类型筛选")
    source_type: str | None = Field(default=None, description="来源类型筛选")
    status: str | None = Field(default=None, description="状态筛选")
    limit: int = Field(default=100, ge=1, le=1000, description="返回条数限制")
    offset: int = Field(default=0, ge=0, description="偏移量（分页）")


class ListConceptRelationsResponse(BaseModel):
    """列表查询概念关系响应 DTO。"""

    total: int = Field(description="符合条件的总记录数")
    items: list[ConceptRelationResponse] = Field(description="关系列表")
    limit: int = Field(description="返回条数限制")
    offset: int = Field(description="偏移量")


# ===== LLM 推荐 =====
class LLMSuggestRequest(BaseModel):
    """LLM 推荐概念关系请求 DTO。"""

    concept_codes_with_names: list[tuple[str, str]] = Field(
        description="概念列表 [(code, name), ...]，需至少 2 个概念"
    )
    min_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="最低置信度阈值（低于此值的关系将被过滤）"
    )


class LLMSuggestResponse(BaseModel):
    """LLM 推荐概念关系响应 DTO。"""

    batch_id: str = Field(description="批次 ID（用于追溯）")
    total_suggested: int = Field(description="LLM 推荐的关系总数")
    created_count: int = Field(description="成功创建的关系数量")
    skipped_count: int = Field(description="跳过的关系数量（重复）")
    message: str = Field(default="LLM 推荐完成", description="提示信息")


# ===== 同步到 Neo4j =====
class SyncConceptRelationsRequest(BaseModel):
    """同步概念关系到 Neo4j 请求 DTO。"""

    mode: str = Field(
        default="incremental",
        description="同步模式（rebuild 全量重建 / incremental 增量追加）",
    )
    batch_size: int = Field(
        default=500, ge=1, le=1000, description="批量写入批次大小"
    )


class SyncConceptRelationsResponse(BaseModel):
    """同步概念关系到 Neo4j 响应 DTO。"""

    mode: str = Field(description="同步模式")
    total_relations: int = Field(description="从 PG 读取的已确认关系总数")
    deleted_count: int = Field(description="Neo4j 中删除的旧关系数量（rebuild 模式）")
    sync_success: int = Field(description="成功同步到 Neo4j 的关系数量")
    sync_failed: int = Field(description="同步失败的关系数量")
    duration_ms: float = Field(description="同步耗时（毫秒）")
    message: str = Field(default="同步完成", description="提示信息")


# ===== 查询概念关系网络 =====
class QueryConceptRelationsRequest(BaseModel):
    """查询概念关系网络请求 DTO（Query 参数）。"""

    direction: str = Field(
        default="both", description="查询方向（outgoing 出边 / incoming 入边 / both 双向）"
    )
    relation_types: list[str] | None = Field(
        default=None, description="关系类型筛选列表（不填则返回所有类型）"
    )


class ConceptRelationQueryItem(BaseModel):
    """概念关系查询结果项 DTO。"""

    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: str = Field(description="关系类型")
    source_type: str = Field(description="来源类型")
    confidence: float = Field(description="置信度")
    pg_id: int | None = Field(default=None, description="PostgreSQL 主键（如果可用）")


class QueryConceptRelationsResponse(BaseModel):
    """查询概念关系网络响应 DTO。"""

    concept_code: str = Field(description="查询的概念代码")
    relations: list[ConceptRelationQueryItem] = Field(description="关系列表")
    total: int = Field(description="关系总数")


# ===== 查询产业链路径 =====
class QueryConceptChainRequest(BaseModel):
    """查询产业链路径请求 DTO（Query 参数）。"""

    direction: str = Field(
        default="outgoing", description="遍历方向（outgoing 下游 / incoming 上游 / both 双向）"
    )
    max_depth: int = Field(
        default=3, ge=1, le=5, description="最大遍历深度"
    )
    relation_types: list[str] | None = Field(
        default=None, description="关系类型筛选列表（不填则返回所有类型）"
    )


class ConceptChainNodeItem(BaseModel):
    """产业链路径节点项 DTO。"""

    concept_code: str = Field(description="概念代码")
    concept_name: str | None = Field(default=None, description="概念名称")
    depth: int = Field(description="从起点的深度（层级）")
    relation_from_previous: str | None = Field(
        default=None, description="与前一个节点的关系类型（起点为 None）"
    )


class QueryConceptChainResponse(BaseModel):
    """查询产业链路径响应 DTO。"""

    concept_code: str = Field(description="起点概念代码")
    direction: str = Field(description="遍历方向")
    max_depth: int = Field(description="最大遍历深度")
    nodes: list[ConceptChainNodeItem] = Field(description="路径节点列表（按深度排序）")
    total_nodes: int = Field(description="节点总数")
