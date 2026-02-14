"""
集成测试：PgConceptRepository CRUD
使用测试 PostgreSQL，验证 upsert_concepts、replace_all_concept_stocks、get_all_concepts_with_stocks
注：需要测试数据库环境才能运行
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.domain.model.concept import Concept, ConceptStock
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_concept_repo import (
    PgConceptRepository,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestPgConceptRepositoryIntegration:
    """PgConceptRepository 集成测试"""

    @pytest.fixture
    async def repository(self, test_db_session: AsyncSession):
        """创建 Repository 实例"""
        return PgConceptRepository(test_db_session)

    @pytest.mark.asyncio
    async def test_upsert_concepts(self, repository):
        """测试 UPSERT 概念记录"""
        concepts = [
            Concept(code="BK0493", name="低空经济"),
            Concept(code="BK0494", name="人形机器人"),
        ]

        # 首次插入
        count = await repository.upsert_concepts(concepts)
        assert count == 2

        # 更新名称
        concepts[0].name = "低空经济-更新"
        count = await repository.upsert_concepts(concepts)
        assert count == 2

        # 验证更新生效
        all_concepts = await repository.get_all_concepts()
        concept_dict = {c.code: c for c in all_concepts}
        assert concept_dict["BK0493"].name == "低空经济-更新"

    @pytest.mark.asyncio
    async def test_replace_all_concept_stocks(self, repository):
        """测试全量替换成份股映射"""
        # 先插入概念
        await repository.upsert_concepts([
            Concept(code="BK0493", name="低空经济"),
        ])

        # 首次插入成份股
        stocks_v1 = [
            ConceptStock(concept_code="BK0493", third_code="000001.SZ", stock_name="平安银行"),
            ConceptStock(concept_code="BK0493", third_code="601398.SH", stock_name="工商银行"),
        ]
        count = await repository.replace_all_concept_stocks(stocks_v1)
        assert count == 2

        # 全量替换
        stocks_v2 = [
            ConceptStock(concept_code="BK0493", third_code="300001.SZ", stock_name="特锐德"),
        ]
        count = await repository.replace_all_concept_stocks(stocks_v2)
        assert count == 1

        # 验证旧数据被清除
        all_stocks = await repository.get_concept_stocks("BK0493")
        assert len(all_stocks) == 1
        assert all_stocks[0].third_code == "300001.SZ"

    @pytest.mark.asyncio
    async def test_get_all_concepts(self, repository):
        """测试查询所有概念"""
        concepts = [
            Concept(code="BK0493", name="低空经济"),
            Concept(code="BK0494", name="人形机器人"),
        ]
        await repository.upsert_concepts(concepts)

        result = await repository.get_all_concepts()
        assert len(result) >= 2
        codes = [c.code for c in result]
        assert "BK0493" in codes
        assert "BK0494" in codes

    @pytest.mark.asyncio
    async def test_get_concept_stocks(self, repository):
        """测试查询指定概念的成份股"""
        await repository.upsert_concepts([
            Concept(code="BK0493", name="低空经济"),
        ])

        stocks = [
            ConceptStock(concept_code="BK0493", third_code="000001.SZ", stock_name="平安银行"),
            ConceptStock(concept_code="BK0493", third_code="601398.SH", stock_name="工商银行"),
        ]
        await repository.replace_all_concept_stocks(stocks)

        result = await repository.get_concept_stocks("BK0493")
        assert len(result) == 2
        codes = [s.third_code for s in result]
        assert "000001.SZ" in codes
        assert "601398.SH" in codes

    @pytest.mark.asyncio
    async def test_get_all_concepts_with_stocks(self, repository):
        """测试聚合查询概念及成份股"""
        # 准备数据
        await repository.upsert_concepts([
            Concept(code="BK0493", name="低空经济"),
            Concept(code="BK0494", name="人形机器人"),
        ])

        stocks = [
            ConceptStock(concept_code="BK0493", third_code="000001.SZ", stock_name="平安银行"),
            ConceptStock(concept_code="BK0493", third_code="601398.SH", stock_name="工商银行"),
            ConceptStock(concept_code="BK0494", third_code="300001.SZ", stock_name="特锐德"),
        ]
        await repository.replace_all_concept_stocks(stocks)

        # 聚合查询
        result = await repository.get_all_concepts_with_stocks()
        assert len(result) >= 2

        concept_dict = {c.code: c for c in result}
        assert len(concept_dict["BK0493"].stocks) == 2
        assert len(concept_dict["BK0494"].stocks) == 1

    @pytest.mark.asyncio
    async def test_upsert_empty_concepts(self, repository):
        """测试空列表 UPSERT"""
        count = await repository.upsert_concepts([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_replace_with_empty_stocks(self, repository):
        """测试清空所有成份股"""
        # 先插入数据
        await repository.upsert_concepts([Concept(code="BK0493", name="低空经济")])
        await repository.replace_all_concept_stocks([
            ConceptStock(concept_code="BK0493", third_code="000001.SZ", stock_name="平安银行"),
        ])

        # 清空
        count = await repository.replace_all_concept_stocks([])
        assert count == 0

        # 验证清空
        result = await repository.get_concept_stocks("BK0493")
        assert len(result) == 0
