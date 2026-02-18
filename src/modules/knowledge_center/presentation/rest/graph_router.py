"""
Knowledge Graph REST API Router。

提供图谱同步与查询的 HTTP 端点。
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.knowledge_center.application.dtos.graph_api_dtos import (
    GraphNodeResponse,
    GraphRelationshipResponse,
    StockGraphResponse,
    StockNeighborResponse,
    SyncGraphRequest,
    SyncGraphResponse,
    SyncStocksFullRequest,
    SyncStocksIncrementalRequest,
    SyncConceptsRequest,
    SyncAllRequest,
)
from src.modules.knowledge_center.application.services.graph_service import GraphService
from src.modules.knowledge_center.container import KnowledgeCenterContainer
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.domain.exceptions import (
    GraphQueryError,
    GraphSyncError,
    Neo4jConnectionError,
)
from src.shared.infrastructure.db.session import get_db_session
from src.shared.dtos import BaseResponse

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])


async def get_graph_service(
    db: AsyncSession = Depends(get_db_session),
) -> GraphService:
    """
    依赖注入：获取 GraphService 实例。
    
    使用请求级 DB session 组装 KnowledgeCenterContainer。
    """
    return KnowledgeCenterContainer(db).graph_service()


def _build_sync_response(result: SyncResult) -> SyncGraphResponse:
    """
    构建同步响应 DTO（私有辅助函数）。
    
    Args:
        result: 同步结果
    
    Returns:
        SyncGraphResponse 实例
    """
    return SyncGraphResponse(
        total=result.total,
        success=result.success,
        failed=result.failed,
        duration_ms=result.duration_ms,
        error_details=result.error_details,
    )


def _merge_sync_results(
    stock_result: SyncResult,
    concept_result: SyncResult,
) -> SyncGraphResponse:
    """
    合并股票和概念同步结果（私有辅助函数）。
    
    Args:
        stock_result: 股票同步结果
        concept_result: 概念同步结果
    
    Returns:
        合并后的 SyncGraphResponse
    """
    return SyncGraphResponse(
        total=stock_result.total + concept_result.total,
        success=stock_result.success + concept_result.success,
        failed=stock_result.failed + concept_result.failed,
        duration_ms=stock_result.duration_ms + concept_result.duration_ms,
        error_details=stock_result.error_details + concept_result.error_details,
    )


@router.get(
    "/stocks/{third_code}/neighbors",
    response_model=BaseResponse[list[StockNeighborResponse]],
    summary="查询同维度股票",
    description="根据指定维度（行业/地域/市场/交易所/概念）查询与目标股票共享同一维度的其他股票",
)
async def get_stock_neighbors(
    third_code: str,
    dimension: Literal["industry", "area", "market", "exchange", "concept"] = Query(
        ...,
        description="维度类型：industry（行业）/ area（地域）/ market（市场）/ exchange（交易所）/ concept（概念）",
    ),
    limit: int = Query(20, ge=1, le=100, description="返回数量上限"),
    dimension_name: str | None = Query(
        None,
        description="维度名称，当 dimension='concept' 时必填，指定概念名称",
    ),
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[list[StockNeighborResponse]]:
    """
    查询同维度股票。
    
    Args:
        third_code: 股票第三方代码
        dimension: 维度类型
        limit: 返回数量上限
        dimension_name: 维度名称，概念维度必填
        service: 图谱服务实例
    
    Returns:
        同维度股票列表
    """
    # 校验概念维度必须提供 dimension_name
    if dimension == "concept" and not dimension_name:
        raise HTTPException(
            status_code=422,
            detail="查询概念维度邻居时必须提供 dimension_name 参数",
        )
    
    try:
        neighbors = await service.get_stock_neighbors(
            third_code=third_code,
            dimension=dimension,
            limit=limit,
            dimension_name=dimension_name,
        )
        
        neighbors_data = [
            StockNeighborResponse(
                third_code=n.third_code,
                name=n.name,
                industry=n.industry,
                area=n.area,
                market=n.market,
                exchange=n.exchange,
            )
            for n in neighbors
        ]
        return BaseResponse(
            success=True,
            code="STOCK_NEIGHBORS_SUCCESS",
            message="同维度股票查询成功",
            data=neighbors_data
        )
    except GraphQueryError as e:
        logger.error(f"查询同维度股票失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"查询同维度股票异常: {str(e)}")
        raise HTTPException(status_code=500, detail="查询失败")


@router.get(
    "/stocks/{third_code}/graph",
    response_model=BaseResponse[StockGraphResponse | None],
    summary="查询个股关系网络",
    description="查询指定股票及其关联的维度节点和关系",
)
async def get_stock_graph(
    third_code: str,
    depth: int = Query(1, ge=1, le=1, description="遍历深度（MVP 阶段仅支持 1）"),
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[StockGraphResponse | None]:
    """
    查询个股关系网络。
    
    Args:
        third_code: 股票第三方代码
        depth: 遍历深度
        service: 图谱服务实例
    
    Returns:
        个股关系网络（节点与关系列表）
    """
    try:
        graph = await service.get_stock_graph(
            third_code=third_code,
            depth=depth,
        )
        
        if not graph:
            return BaseResponse(
                success=True,
                code="STOCK_GRAPH_SUCCESS",
                message="个股关系网络查询成功，无数据",
                data=None
            )
        
        graph_data = StockGraphResponse(
            nodes=[
                GraphNodeResponse(
                    label=n.label,
                    id=n.id,
                    properties=n.properties,
                )
                for n in graph.nodes
            ],
            relationships=[
                GraphRelationshipResponse(
                    source_id=r.source_id,
                    target_id=r.target_id,
                    relationship_type=r.relationship_type,
                )
                for r in graph.relationships
            ],
        )
        return BaseResponse(
            success=True,
            code="STOCK_GRAPH_SUCCESS",
            message="个股关系网络查询成功",
            data=graph_data
        )
    except GraphQueryError as e:
        logger.error(f"查询个股关系网络失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询个股关系网络异常: {str(e)}")
        raise HTTPException(status_code=500, detail="查询失败")


@router.post(
    "/sync/stocks/full",
    response_model=BaseResponse[SyncGraphResponse],
    summary="股票全量同步",
    description="全量同步股票数据到 Neo4j 图谱",
)
async def sync_stocks_full(
    request: SyncStocksFullRequest,
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[SyncGraphResponse]:
    """
    股票全量同步。
    
    Args:
        request: 同步请求参数
        service: 图谱服务实例
    
    Returns:
        同步结果摘要
    """
    try:
        logger.info("执行股票全量同步")
        result = await service.sync_full_graph(
            include_finance=request.include_finance,
            batch_size=request.batch_size,
            skip=request.skip,
            limit=request.limit,
        )
        
        return BaseResponse(
            success=True,
            code="GRAPH_SYNC_SUCCESS",
            message="股票数据全量同步成功",
            data=_build_sync_response(result)
        )
    except GraphSyncError as e:
        logger.error(f"同步股票数据失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Neo4jConnectionError as e:
        logger.error(f"Neo4j 连接失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"同步股票数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")


@router.post(
    "/sync/stocks/incremental",
    response_model=BaseResponse[SyncGraphResponse],
    summary="股票增量同步",
    description="增量同步股票数据到 Neo4j 图谱",
)
async def sync_stocks_incremental(
    request: SyncStocksIncrementalRequest,
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[SyncGraphResponse]:
    """
    股票增量同步。
    
    Args:
        request: 同步请求参数
        service: 图谱服务实例
    
    Returns:
        同步结果摘要
    """
    try:
        logger.info(f"执行股票增量同步 {len(request.third_codes or [])} 只股票")
        result = await service.sync_incremental_graph(
            third_codes=request.third_codes,
            include_finance=request.include_finance,
            batch_size=request.batch_size,
            window_days=request.window_days,
            limit=request.limit,
        )
        
        return BaseResponse(
            success=True,
            code="GRAPH_SYNC_SUCCESS",
            message="股票数据增量同步成功",
            data=_build_sync_response(result)
        )
    except GraphSyncError as e:
        logger.error(f"同步股票数据失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Neo4jConnectionError as e:
        logger.error(f"Neo4j 连接失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"同步股票数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")


@router.post(
    "/sync/concepts",
    response_model=BaseResponse[SyncGraphResponse],
    summary="概念同步",
    description="全量同步概念数据到 Neo4j 图谱",
)
async def sync_concepts(
    request: SyncConceptsRequest,
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[SyncGraphResponse]:
    """
    概念同步。
    
    Args:
        request: 同步请求参数
        service: 图谱服务实例
    
    Returns:
        同步结果摘要
    """
    try:
        logger.info("执行概念全量同步")
        result = await service.sync_concept_graph(batch_size=request.batch_size)
        
        return BaseResponse(
            success=True,
            code="GRAPH_SYNC_SUCCESS",
            message="概念数据同步成功",
            data=_build_sync_response(result)
        )
    except GraphSyncError as e:
        logger.error(f"同步概念数据失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Neo4jConnectionError as e:
        logger.error(f"Neo4j 连接失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"同步概念数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")


@router.post(
    "/sync/all",
    response_model=BaseResponse[SyncGraphResponse],
    summary="全部同步",
    description="同步股票和概念数据到 Neo4j 图谱",
)
async def sync_all(
    request: SyncAllRequest,
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[SyncGraphResponse]:
    """
    全部同步（股票 + 概念）。
    
    Args:
        request: 同步请求参数
        service: 图谱服务实例
    
    Returns:
        同步结果摘要
    """
    try:
        logger.info("执行全部同步：股票 + 概念")
        
        # 执行股票同步
        if request.mode == "full":
            stock_result = await service.sync_full_graph(
                include_finance=request.include_finance,
                batch_size=request.batch_size,
                skip=request.skip,
                limit=request.limit,
            )
        else:
            stock_result = await service.sync_incremental_graph(
                third_codes=request.third_codes,
                include_finance=request.include_finance,
                batch_size=request.batch_size,
                window_days=request.window_days,
                limit=request.limit,
            )
        
        # 执行概念同步
        concept_result = await service.sync_concept_graph(batch_size=request.batch_size)
        
        # 合并结果
        merged_result = _merge_sync_results(stock_result, concept_result)
        
        return BaseResponse(
            success=True,
            code="GRAPH_SYNC_SUCCESS",
            message="全部数据同步成功",
            data=merged_result
        )
    except GraphSyncError as e:
        logger.error(f"同步数据失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Neo4jConnectionError as e:
        logger.error(f"Neo4j 连接失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"同步数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")


@router.post(
    "/sync",
    response_model=BaseResponse[SyncGraphResponse],
    summary="同步图谱数据（Deprecated）",
    description="【已弃用】请使用专用同步端点：/sync/stocks/full、/sync/stocks/incremental、/sync/concepts、/sync/all",
    deprecated=True,
)
async def sync_graph(
    request: SyncGraphRequest,
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[SyncGraphResponse]:
    """
    同步图谱数据（已弃用，保持向后兼容）。
    
    Args:
        request: 同步请求参数
        service: 图谱服务实例
    
    Returns:
        同步结果摘要
    """
    try:
        # 根据 target 参数分发到对应同步命令
        if request.target == "concept":
            # 概念同步仅支持全量模式
            logger.warning("使用已弃用的 /sync 接口，请迁移到 /sync/concepts")
            logger.info("执行概念图谱全量同步")
            result = await service.sync_concept_graph(batch_size=request.batch_size)
        elif request.target == "all":
            # 依次执行股票同步和概念同步
            logger.warning("使用已弃用的 /sync 接口，请迁移到 /sync/all")
            logger.info("执行全部同步：股票 + 概念")
            if request.mode == "full":
                stock_result = await service.sync_full_graph(
                    include_finance=request.include_finance,
                    batch_size=request.batch_size,
                    skip=request.skip,
                    limit=request.limit,
                )
            else:
                stock_result = await service.sync_incremental_graph(
                    third_codes=request.third_codes,
                    include_finance=request.include_finance,
                    batch_size=request.batch_size,
                    window_days=request.window_days,
                    limit=request.limit,
                )
            
            concept_result = await service.sync_concept_graph(batch_size=request.batch_size)
            
            # 合并结果
            result = _merge_sync_results(stock_result, concept_result)
            return BaseResponse(
                success=True,
                code="GRAPH_SYNC_SUCCESS",
                message="图谱数据同步成功",
                data=result
            )
        else:
            # target="stock" 的默认行为
            logger.warning("使用已弃用的 /sync 接口，请迁移到专用同步端点")
            if request.mode == "full":
                result = await service.sync_full_graph(
                    include_finance=request.include_finance,
                    batch_size=request.batch_size,
                    skip=request.skip,
                    limit=request.limit,
                )
            elif request.mode == "incremental":
                result = await service.sync_incremental_graph(
                    third_codes=request.third_codes,
                    include_finance=request.include_finance,
                    batch_size=request.batch_size,
                    window_days=request.window_days,
                    limit=request.limit,
                )
            else:
                raise HTTPException(status_code=400, detail=f"无效的同步模式: {request.mode}")
        
        return BaseResponse(
            success=True,
            code="GRAPH_SYNC_SUCCESS",
            message="图谱数据同步成功",
            data=_build_sync_response(result)
        )
    except GraphSyncError as e:
        logger.error(f"同步图谱数据失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Neo4jConnectionError as e:
        logger.error(f"Neo4j 连接失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步图谱数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")


@router.delete(
    "/clear",
    response_model=BaseResponse[dict],
    summary="清空知识图谱",
    description="删除所有图谱节点和关系，用于完全重建图谱。此操作不可逆，请谨慎使用！",
)
async def clear_graph(
    service: GraphService = Depends(get_graph_service),
) -> BaseResponse[dict]:
    """
    清空知识图谱。
    
    删除所有节点和关系，用于完全重建图谱。
    
    Returns:
        清空结果统计信息
    """
    try:
        result = await service.clear_all_graph_data()
        return BaseResponse(
            success=True,
            code="GRAPH_CLEAR_SUCCESS",
            message="知识图谱清空成功",
            data=result
        )
    except GraphSyncError as e:
        logger.error(f"清空图谱失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Neo4jConnectionError as e:
        logger.error(f"Neo4j 连接失败: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"清空图谱异常: {str(e)}")
        raise HTTPException(status_code=500, detail="清空失败")
