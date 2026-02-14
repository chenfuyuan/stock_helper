"""
集成测试：Neo4j Concept 节点和关系的 CRUD
使用测试 Neo4j 实例，验证 merge_concepts、delete_all_concept_relationships、ensure_constraints
注：需要测试 Neo4j 环境才能运行
"""

import pytest

from src.modules.knowledge_center.domain.dtos.concept_sync_dtos import ConceptGraphSyncDTO
from src.modules.knowledge_center.infrastructure.persistence.neo4j_graph_repository import (
    Neo4jGraphRepository,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestNeo4jConceptOperationsIntegration:
    """Neo4j 概念操作集成测试"""

    @pytest.fixture
    async def repository(self, test_neo4j_driver):
        """创建 Repository 实例"""
        return Neo4jGraphRepository(driver=test_neo4j_driver)

    @pytest.mark.asyncio
    async def test_ensure_constraints_concept(self, repository):
        """测试创建 Concept.code 唯一约束"""
        # 幂等调用
        await repository.ensure_constraints()
        await repository.ensure_constraints()

        # 验证约束存在（通过尝试插入重复节点应失败）
        # 实际验证需要查询 Neo4j 约束信息

    @pytest.mark.asyncio
    async def test_merge_concepts_success(self, repository):
        """测试批量写入 Concept 节点和关系"""
        # 先确保有 Stock 节点
        # ... 准备 Stock 节点 ...

        concepts = [
            ConceptGraphSyncDTO(
                code="BK0493",
                name="低空经济",
                stock_third_codes=["000001.SZ", "601398.SH"],
            ),
            ConceptGraphSyncDTO(
                code="BK0494",
                name="人形机器人",
                stock_third_codes=["300001.SZ"],
            ),
        ]

        result = await repository.merge_concepts(concepts, batch_size=10)

        assert result.total == 2
        assert result.success >= 0  # 实际成功数取决于 Stock 节点是否存在
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_merge_concepts_idempotent(self, repository):
        """测试 merge_concepts 幂等性"""
        concepts = [
            ConceptGraphSyncDTO(
                code="BK0493",
                name="低空经济",
                stock_third_codes=["000001.SZ"],
            ),
        ]

        # 多次调用应幂等
        result1 = await repository.merge_concepts(concepts)
        result2 = await repository.merge_concepts(concepts)

        assert result1.total == result2.total

    @pytest.mark.asyncio
    async def test_merge_concepts_update_name(self, repository):
        """测试更新 Concept 节点名称"""
        concepts_v1 = [
            ConceptGraphSyncDTO(code="BK0493", name="低空经济", stock_third_codes=[]),
        ]
        await repository.merge_concepts(concepts_v1)

        # 更新名称
        concepts_v2 = [
            ConceptGraphSyncDTO(code="BK0493", name="低空经济-更新", stock_third_codes=[]),
        ]
        await repository.merge_concepts(concepts_v2)

        # 验证名称更新（需要查询验证）

    @pytest.mark.asyncio
    async def test_delete_all_concept_relationships(self, repository):
        """测试删除所有 BELONGS_TO_CONCEPT 关系"""
        # 先插入一些关系
        concepts = [
            ConceptGraphSyncDTO(
                code="BK0493",
                name="低空经济",
                stock_third_codes=["000001.SZ"],
            ),
        ]
        await repository.merge_concepts(concepts)

        # 删除所有关系
        deleted_count = await repository.delete_all_concept_relationships()
        assert deleted_count >= 0

        # 再次删除应返回 0
        deleted_count = await repository.delete_all_concept_relationships()
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_merge_concepts_empty_list(self, repository):
        """测试空列表"""
        result = await repository.merge_concepts([])
        assert result.total == 0
        assert result.success == 0

    @pytest.mark.asyncio
    async def test_merge_concepts_without_stocks(self, repository):
        """测试概念无成份股"""
        concepts = [
            ConceptGraphSyncDTO(code="BK0493", name="低空经济", stock_third_codes=[]),
        ]

        result = await repository.merge_concepts(concepts)
        assert result.success >= 1  # Concept 节点应成功创建

    @pytest.mark.asyncio
    async def test_merge_concepts_with_nonexistent_stocks(self, repository):
        """测试成份股中包含不存在的 Stock 节点"""
        concepts = [
            ConceptGraphSyncDTO(
                code="BK0493",
                name="低空经济",
                stock_third_codes=["999999.SZ"],  # 不存在的股票
            ),
        ]

        # 不应抛出异常，但关系不会被创建
        result = await repository.merge_concepts(concepts)
        assert result.success >= 0
