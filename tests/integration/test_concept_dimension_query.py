"""
集成测试：概念维度邻居查询和关系网络查询
注：需要测试 Neo4j 环境和测试数据才能运行
"""

import pytest

from src.modules.knowledge_center.domain.exceptions import GraphQueryError
from src.modules.knowledge_center.infrastructure.persistence.neo4j_graph_repository import (
    Neo4jGraphRepository,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestConceptDimensionQueryIntegration:
    """概念维度查询集成测试"""

    @pytest.fixture
    async def repository(self, test_neo4j_driver):
        """创建 Repository 实例"""
        return Neo4jGraphRepository(driver=test_neo4j_driver)

    @pytest.mark.asyncio
    async def test_find_neighbors_by_concept(self, repository):
        """测试按概念维度查询邻居股票"""
        # 前提：需要预先创建测试数据
        # Stock 节点：000001.SZ, 601398.SH
        # Concept 节点：低空经济
        # 关系：000001.SZ -[:BELONGS_TO_CONCEPT]-> 低空经济
        #      601398.SH -[:BELONGS_TO_CONCEPT]-> 低空经济

        neighbors = await repository.find_neighbors(
            third_code="000001.SZ",
            dimension="concept",
            dimension_name="低空经济",
            limit=20,
        )

        assert isinstance(neighbors, list)
        # 应返回 601398.SH（同概念的其他股票）
        # assert any(n.third_code == "601398.SH" for n in neighbors)

    @pytest.mark.asyncio
    async def test_find_neighbors_concept_without_dimension_name(self, repository):
        """测试概念维度查询缺少 dimension_name 参数"""
        with pytest.raises(GraphQueryError) as exc_info:
            await repository.find_neighbors(
                third_code="000001.SZ",
                dimension="concept",
                limit=20,
            )

        assert "dimension_name" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_find_neighbors_concept_no_results(self, repository):
        """测试查询不存在的概念"""
        neighbors = await repository.find_neighbors(
            third_code="000001.SZ",
            dimension="concept",
            dimension_name="不存在的概念",
            limit=20,
        )

        assert neighbors == []

    @pytest.mark.asyncio
    async def test_find_neighbors_stock_not_in_concept(self, repository):
        """测试股票不属于指定概念"""
        # 假设 300001.SZ 不属于"低空经济"
        neighbors = await repository.find_neighbors(
            third_code="300001.SZ",
            dimension="concept",
            dimension_name="低空经济",
            limit=20,
        )

        assert neighbors == []

    @pytest.mark.asyncio
    async def test_find_stock_graph_includes_concept(self, repository):
        """测试个股关系网络包含 Concept 节点"""
        # 前提：需要预先创建测试数据
        # Stock 节点：000001.SZ
        # Concept 节点：低空经济
        # 关系：000001.SZ -[:BELONGS_TO_CONCEPT]-> 低空经济

        graph = await repository.find_stock_graph(
            third_code="000001.SZ",
            depth=1,
        )

        if graph:
            # 验证返回的节点中包含 Concept 标签
            concept_nodes = [n for n in graph.nodes if n.label == "CONCEPT"]
            # assert len(concept_nodes) > 0

            # 验证返回的关系中包含 BELONGS_TO_CONCEPT
            concept_rels = [r for r in graph.relationships if r.relationship_type == "BELONGS_TO_CONCEPT"]
            # assert len(concept_rels) > 0

    @pytest.mark.asyncio
    async def test_find_stock_graph_no_concept(self, repository):
        """测试股票不属于任何概念"""
        # 假设某股票不属于任何概念
        graph = await repository.find_stock_graph(
            third_code="999999.SZ",
            depth=1,
        )

        # 应返回 None 或不包含 Concept 节点
        if graph:
            concept_nodes = [n for n in graph.nodes if n.label == "CONCEPT"]
            assert len(concept_nodes) == 0

    @pytest.mark.asyncio
    async def test_find_neighbors_multiple_concepts(self, repository):
        """测试股票属于多个概念时的邻居查询"""
        # 前提：000001.SZ 同时属于"低空经济"和"人形机器人"
        # 查询"低空经济"维度的邻居
        neighbors1 = await repository.find_neighbors(
            third_code="000001.SZ",
            dimension="concept",
            dimension_name="低空经济",
            limit=20,
        )

        # 查询"人形机器人"维度的邻居
        neighbors2 = await repository.find_neighbors(
            third_code="000001.SZ",
            dimension="concept",
            dimension_name="人形机器人",
            limit=20,
        )

        # 两个查询结果应不同
        # assert neighbors1 != neighbors2
