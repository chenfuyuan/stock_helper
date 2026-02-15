"""
概念关系 REST API Router。

提供概念关系的 CRUD、LLM 推荐、同步、查询等 HTTP 端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.knowledge_center.application.commands.suggest_concept_relations_command import (
    SuggestConceptRelationsCmd,
)
from src.modules.knowledge_center.application.commands.sync_concept_relations_command import (
    SyncConceptRelationsCmd,
)
from src.modules.knowledge_center.application.dtos.concept_relation_dtos import (
    ConceptChainNodeItem,
    ConceptRelationQueryItem,
    ConceptRelationResponse,
    CreateConceptRelationRequest,
    ListConceptRelationsResponse,
    LLMSuggestRequest,
    LLMSuggestResponse,
    QueryConceptChainResponse,
    QueryConceptRelationsResponse,
    SyncConceptRelationsRequest,
    SyncConceptRelationsResponse,
    UpdateConceptRelationRequest,
)
from src.modules.knowledge_center.application.services.concept_relation_service import (
    ConceptRelationService,
)
from src.modules.knowledge_center.container import KnowledgeCenterContainer
from src.modules.knowledge_center.domain.exceptions import GraphQueryError
from src.shared.infrastructure.db.session import get_db_session

router = APIRouter(
    prefix="/knowledge-graph/concept-relations", tags=["Concept Relations"]
)


async def get_concept_relation_service(
    db: AsyncSession = Depends(get_db_session),
) -> ConceptRelationService:
    """依赖注入：获取 ConceptRelationService 实例。"""
    return KnowledgeCenterContainer(db).concept_relation_service()


async def get_suggest_cmd(
    db: AsyncSession = Depends(get_db_session),
) -> SuggestConceptRelationsCmd:
    """依赖注入：获取 SuggestConceptRelationsCmd 实例。"""
    return KnowledgeCenterContainer(db).suggest_concept_relations_cmd()


async def get_sync_cmd(
    db: AsyncSession = Depends(get_db_session),
) -> SyncConceptRelationsCmd:
    """依赖注入：获取 SyncConceptRelationsCmd 实例。"""
    return KnowledgeCenterContainer(db).sync_concept_relations_cmd()


# ===== CRUD 端点 =====
@router.post(
    "",
    response_model=ConceptRelationResponse,
    status_code=201,
    summary="创建概念关系（手动）",
    description="手动创建概念间关系，状态默认为 CONFIRMED",
)
async def create_concept_relation(
    request: CreateConceptRelationRequest,
    service: ConceptRelationService = Depends(get_concept_relation_service),
):
    """创建概念关系（手动）。"""
    try:
        created = await service.create_manual_relation(
            source_concept_code=request.source_concept_code,
            target_concept_code=request.target_concept_code,
            relation_type=request.relation_type,
            note=request.note,
            reason=request.reason,
            created_by="api_user",  # TODO: 从认证上下文获取
        )
        return ConceptRelationResponse(**created.model_dump())
    except Exception as e:
        logger.error(f"创建概念关系失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=ListConceptRelationsResponse,
    summary="列表查询概念关系",
    description="支持多条件筛选的概念关系列表查询",
)
async def list_concept_relations(
    source_concept_code: str | None = Query(None, description="源概念代码筛选"),
    target_concept_code: str | None = Query(None, description="目标概念代码筛选"),
    relation_type: str | None = Query(None, description="关系类型筛选"),
    source_type: str | None = Query(None, description="来源类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: ConceptRelationService = Depends(get_concept_relation_service),
):
    """列表查询概念关系。"""
    try:
        relations = await service.list_relations(
            source_concept_code=source_concept_code,
            target_concept_code=target_concept_code,
            relation_type=relation_type,
            source_type=source_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        
        total = await service.count(
            source_concept_code=source_concept_code,
            target_concept_code=target_concept_code,
            relation_type=relation_type,
            source_type=source_type,
            status=status,
        )
        
        items = [ConceptRelationResponse(**r.model_dump()) for r in relations]
        
        return ListConceptRelationsResponse(
            total=total,
            items=items,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"查询概念关系列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{relation_id}",
    response_model=ConceptRelationResponse,
    summary="查询单条概念关系",
    description="根据 ID 查询单条概念关系记录",
)
async def get_concept_relation(
    relation_id: int,
    service: ConceptRelationService = Depends(get_concept_relation_service),
):
    """查询单条概念关系。"""
    relation = await service.get_by_id(relation_id)
    if not relation:
        raise HTTPException(status_code=404, detail=f"概念关系不存在: id={relation_id}")
    return ConceptRelationResponse(**relation.model_dump())


@router.put(
    "/{relation_id}",
    response_model=ConceptRelationResponse,
    summary="更新概念关系",
    description="更新概念关系（主要用于确认或拒绝 LLM 推荐）",
)
async def update_concept_relation(
    relation_id: int,
    request: UpdateConceptRelationRequest,
    service: ConceptRelationService = Depends(get_concept_relation_service),
):
    """更新概念关系。"""
    try:
        if request.status:
            updated = await service.update_status(relation_id, request.status)
            return ConceptRelationResponse(**updated.model_dump())
        else:
            raise HTTPException(status_code=400, detail="未提供更新字段")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新概念关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{relation_id}",
    status_code=204,
    summary="删除概念关系",
    description="删除指定 ID 的概念关系记录",
)
async def delete_concept_relation(
    relation_id: int,
    service: ConceptRelationService = Depends(get_concept_relation_service),
):
    """删除概念关系。"""
    success = await service.delete(relation_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"概念关系不存在: id={relation_id}")
    return None


# ===== LLM 推荐端点 =====
@router.post(
    "/llm-suggest",
    response_model=LLMSuggestResponse,
    summary="LLM 推荐概念关系",
    description="基于 LLM 分析推荐概念间关系，结果写入 PostgreSQL 待人工确认",
)
async def llm_suggest_relations(
    request: LLMSuggestRequest,
    cmd: SuggestConceptRelationsCmd = Depends(get_suggest_cmd),
):
    """LLM 推荐概念关系。"""
    try:
        result = await cmd.execute(
            concept_codes_with_names=request.concept_codes_with_names,
            created_by="api_user",  # TODO: 从认证上下文获取
            min_confidence=request.min_confidence,
        )
        
        return LLMSuggestResponse(
            batch_id=result.batch_id,
            total_suggested=result.total_suggested,
            created_count=result.created_count,
            skipped_count=result.skipped_count,
            message=f"LLM 推荐完成，推荐 {result.total_suggested} 条，创建 {result.created_count} 条",
        )
    except Exception as e:
        logger.error(f"LLM 推荐概念关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 同步端点 =====
@router.post(
    "/sync",
    response_model=SyncConceptRelationsResponse,
    summary="同步概念关系到 Neo4j",
    description="将 PostgreSQL 中已确认的概念关系同步到 Neo4j 图谱",
)
async def sync_concept_relations(
    request: SyncConceptRelationsRequest,
    cmd: SyncConceptRelationsCmd = Depends(get_sync_cmd),
):
    """同步概念关系到 Neo4j。"""
    try:
        result = await cmd.execute(
            mode=request.mode,
            batch_size=request.batch_size,
        )
        
        return SyncConceptRelationsResponse(
            mode=result.mode,
            total_relations=result.total_relations,
            deleted_count=result.deleted_count,
            sync_success=result.sync_result.success,
            sync_failed=result.sync_result.failed,
            duration_ms=result.sync_result.duration_ms,
            message=f"同步完成，成功 {result.sync_result.success} 条，失败 {result.sync_result.failed} 条",
        )
    except Exception as e:
        logger.error(f"同步概念关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 图谱查询端点（需要注册到主 graph router 或单独路由）=====
# 这些端点路径与 concept-relations 不同，应挂载到 /knowledge-graph/concepts 下
concept_query_router = APIRouter(
    prefix="/knowledge-graph/concepts", tags=["Concept Relations Query"]
)


@concept_query_router.get(
    "/{code}/relations",
    response_model=QueryConceptRelationsResponse,
    summary="查询概念关系网络",
    description="查询指定概念的直接关系（上下游、竞争等）",
)
async def query_concept_relations(
    code: str,
    direction: str = Query("both", description="查询方向（outgoing / incoming / both）"),
    relation_types: list[str] | None = Query(None, description="关系类型筛选列表"),
    db: AsyncSession = Depends(get_db_session),
):
    """查询概念关系网络。"""
    try:
        container = KnowledgeCenterContainer(db)
        graph_repo = container.graph_repository()
        
        relations = await graph_repo.find_concept_relations(
            concept_code=code,
            direction=direction,
            relation_types=relation_types,
        )
        
        items = [
            ConceptRelationQueryItem(
                source_concept_code=r.source_concept_code,
                target_concept_code=r.target_concept_code,
                relation_type=r.relation_type,
                source_type=r.source_type,
                confidence=r.confidence,
                pg_id=r.pg_id,
            )
            for r in relations
        ]
        
        return QueryConceptRelationsResponse(
            concept_code=code,
            relations=items,
            total=len(items),
        )
    except GraphQueryError as e:
        logger.error(f"查询概念关系网络失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@concept_query_router.get(
    "/{code}/chain",
    response_model=QueryConceptChainResponse,
    summary="查询产业链路径",
    description="查询指定概念的产业链路径（变长路径遍历）",
)
async def query_concept_chain(
    code: str,
    direction: str = Query("outgoing", description="遍历方向（outgoing / incoming / both）"),
    max_depth: int = Query(3, ge=1, le=5, description="最大遍历深度"),
    relation_types: list[str] | None = Query(None, description="关系类型筛选列表"),
    db: AsyncSession = Depends(get_db_session),
):
    """查询产业链路径。"""
    try:
        container = KnowledgeCenterContainer(db)
        graph_repo = container.graph_repository()
        
        nodes = await graph_repo.find_concept_chain(
            concept_code=code,
            direction=direction,
            max_depth=max_depth,
            relation_types=relation_types,
        )
        
        items = [
            ConceptChainNodeItem(
                concept_code=n.concept_code,
                concept_name=n.concept_name,
                depth=n.depth,
                relation_from_previous=n.relation_from_previous,
            )
            for n in nodes
        ]
        
        return QueryConceptChainResponse(
            concept_code=code,
            direction=direction,
            max_depth=max_depth,
            nodes=items,
            total_nodes=len(items),
        )
    except GraphQueryError as e:
        logger.error(f"查询产业链路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
