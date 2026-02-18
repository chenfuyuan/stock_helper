import uuid
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.dtos.concept_dtos import ConceptWithStocksDTO
from src.modules.data_engineering.domain.model.concept import Concept, ConceptStock
from src.modules.data_engineering.domain.ports.repositories.concept_repo import (
    IConceptRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.concept_model import (
    ConceptModel,
    ConceptStockModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class PgConceptRepository(BaseRepository[ConceptModel], IConceptRepository):
    """
    PostgreSQL 概念数据仓储实现
    实现 IConceptRepository 接口
    """

    def __init__(self, session):
        super().__init__(ConceptModel, session)

    async def upsert_concept_with_stocks(self, concept: Concept, stocks: list[ConceptStock]) -> int:
        """
        在一个事务中完成概念 UPSERT 和成份股替换
        
        Args:
            concept: 概念对象
            stocks: 成份股列表
            
        Returns:
            int: 总影响的行数（概念1行 + 成份股行数）
        """
        # UPSERT 概念记录
        concept_data = concept.model_dump(exclude={"id"}, exclude_unset=True)
        concept_stmt = insert(ConceptModel).values(**concept_data)
        concept_stmt = concept_stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name": concept_stmt.excluded.name,
                "updated_at": concept_stmt.excluded.updated_at,
            },
        )
        await self.session.execute(concept_stmt)
        
        # 替换该概念的成份股映射
        await self.session.execute(
            delete(ConceptStockModel).where(ConceptStockModel.concept_code == concept.code)
        )
        
        total_rows = 1  # 概念记录1行
        
        if stocks:
            mapping_dicts = [
                stock.model_dump(exclude={"id"}, exclude_unset=True) for stock in stocks
            ]
            await self.session.execute(insert(ConceptStockModel).values(mapping_dicts))
            total_rows += len(stocks)
        
        # 统一提交事务
        await self.session.commit()
        
        logger.debug(f"概念 {concept.code} 事务提交：概念1行，成份股{len(stocks)}行")
        return total_rows

    async def upsert_concept(self, concept: Concept) -> int:
        """
        单个概念 UPSERT（by code）
        
        Args:
            concept: 概念对象
            
        Returns:
            int: 影响的行数
        """
        concept_data = concept.model_dump(exclude={"id"}, exclude_unset=True)

        stmt = insert(ConceptModel).values(**concept_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name": stmt.excluded.name,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()
        logger.debug(f"UPSERT 1 条概念记录：{concept.code}")
        return 1

    async def replace_concept_stocks(self, concept_code: str, stocks: list[ConceptStock]) -> int:
        """
        替换指定概念的成份股映射（先清后建）
        
        Args:
            concept_code: 概念板块代码
            stocks: 成份股列表
            
        Returns:
            int: 插入的行数
        """
        # 先删除该概念的所有现有映射
        await self.session.execute(
            delete(ConceptStockModel).where(ConceptStockModel.concept_code == concept_code)
        )
        logger.debug(f"已清空概念 {concept_code} 的成份股映射")

        if not stocks:
            await self.session.commit()
            return 0

        # 批量插入新映射
        mapping_dicts = [
            stock.model_dump(exclude={"id"}, exclude_unset=True) for stock in stocks
        ]
        await self.session.execute(insert(ConceptStockModel).values(mapping_dicts))
        await self.session.commit()

        inserted_count = len(stocks)
        logger.debug(f"为概念 {concept_code} 插入 {inserted_count} 条成份股映射")
        return inserted_count

    async def upsert_concepts(self, concepts: list[Concept]) -> int:
        """
        批量 UPSERT 概念记录（by code）
        使用 PostgreSQL ON CONFLICT DO UPDATE 实现幂等写入
        
        Args:
            concepts: 概念列表
            
        Returns:
            int: 影响的行数
        """
        if not concepts:
            return 0

        rows_affected = 0
        for concept in concepts:
            concept_data = concept.model_dump(exclude={"id"}, exclude_unset=True)

            stmt = insert(ConceptModel).values(**concept_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "name": stmt.excluded.name,
                    "updated_at": stmt.excluded.updated_at,
                },
            )

            await self.session.execute(stmt)
            rows_affected += 1

        await self.session.commit()
        logger.debug(f"UPSERT {rows_affected} 条概念记录")
        return rows_affected

    async def replace_all_concept_stocks(self, mappings: list[ConceptStock]) -> int:
        """
        全量替换 concept_stock 表（先清后建）
        
        Args:
            mappings: 概念-股票映射列表
            
        Returns:
            int: 插入的行数
        """
        # 先删除所有现有映射
        await self.session.execute(delete(ConceptStockModel))
        logger.debug("已清空 concept_stock 表")

        if not mappings:
            await self.session.commit()
            return 0

        # 批量插入新映射
        mapping_dicts = [
            mapping.model_dump(exclude={"id"}, exclude_unset=True) for mapping in mappings
        ]
        await self.session.execute(insert(ConceptStockModel).values(mapping_dicts))
        await self.session.commit()

        inserted_count = len(mappings)
        logger.debug(f"插入 {inserted_count} 条概念-股票映射")
        return inserted_count

    async def get_all_concepts(self) -> list[Concept]:
        """
        查询所有概念记录
        
        Returns:
            list[Concept]: 概念列表
        """
        result = await self.session.execute(select(ConceptModel))
        models = result.scalars().all()
        return [Concept.model_validate({
            'id': uuid.uuid4(),  # 生成新的 UUID
            'code': model.code,
            'name': model.name,
            'created_at': model.created_at,
            'updated_at': model.updated_at,
        }) for model in models]

    async def get_concept_stocks(self, concept_code: str) -> list[ConceptStock]:
        """
        查询指定概念的成份股
        
        Args:
            concept_code: 概念板块代码
            
        Returns:
            list[ConceptStock]: 成份股列表
        """
        result = await self.session.execute(
            select(ConceptStockModel).where(ConceptStockModel.concept_code == concept_code)
        )
        models = result.scalars().all()
        return [ConceptStock.model_validate({
            'id': uuid.uuid4(),  # 生成新的 UUID
            'concept_code': model.concept_code,
            'third_code': model.third_code,
            'stock_name': model.stock_name,
            'created_at': model.created_at,
            'updated_at': model.created_at,  # 数据库模型没有 updated_at，使用 created_at
        }) for model in models]

    async def get_all_concepts_with_stocks(self) -> list[ConceptWithStocksDTO]:
        """
        查询所有概念及其成份股（聚合查询，供 KC 适配器使用）
        
        Returns:
            list[ConceptWithStocksDTO]: 概念及成份股聚合列表
        """
        # 查询所有概念
        concepts_result = await self.session.execute(select(ConceptModel))
        concept_models = concepts_result.scalars().all()

        if not concept_models:
            return []

        # 查询所有成份股映射
        stocks_result = await self.session.execute(select(ConceptStockModel))
        stock_models = stocks_result.scalars().all()

        # 按 concept_code 分组
        stocks_by_concept: dict[str, list[ConceptStock]] = {}
        for stock_model in stock_models:
            concept_code = stock_model.concept_code
            if concept_code not in stocks_by_concept:
                stocks_by_concept[concept_code] = []
            stocks_by_concept[concept_code].append(ConceptStock.model_validate({
                'id': uuid.uuid4(),  # 生成新的 UUID
                'concept_code': stock_model.concept_code,
                'third_code': stock_model.third_code,
                'stock_name': stock_model.stock_name,
                'created_at': stock_model.created_at,
                'updated_at': stock_model.created_at,  # 数据库模型没有 updated_at，使用 created_at
            }))

        # 组装 DTO
        result_dtos: list[ConceptWithStocksDTO] = []
        for concept_model in concept_models:
            result_dtos.append(
                ConceptWithStocksDTO(
                    code=concept_model.code,
                    name=concept_model.name,
                    stocks=stocks_by_concept.get(concept_model.code, []),
                )
            )

        logger.debug(f"查询到 {len(result_dtos)} 个概念及其成份股")
        return result_dtos
