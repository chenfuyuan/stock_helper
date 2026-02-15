"""
Neo4jGraphRepository 概念关系方法集成测试。

连接测试 Neo4j，验证概念关系的 MERGE、删除、查询、链路遍历操作。
"""

import pytest

from src.modules.knowledge_center.domain.dtos.concept_relation_query_dtos import (
    ConceptChainNodeDTO,
    ConceptRelationQueryDTO,
)
from src.modules.knowledge_center.domain.dtos.concept_relation_sync_dtos import (
    ConceptRelationSyncDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.infrastructure.persistence.neo4j_graph_repository import (
    Neo4jGraphRepository,
)


class TestNeo4jConceptRelationsIntegration:
    """Neo4j 概念关系集成测试类。"""

    @pytest.fixture
    async def repository(self, neo4j_driver) -> Neo4jGraphRepository:
        """创建图谱仓储实例。"""
        return Neo4jGraphRepository(neo4j_driver)

    @pytest.fixture
    async def sample_concept_relations(self) -> list[ConceptRelationSyncDTO]:
        """示例概念关系同步数据。"""
        return [
            ConceptRelationSyncDTO(
                pg_id=1,
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
            ConceptRelationSyncDTO(
                pg_id=2,
                source_concept_code="CHIP",
                target_concept_code="AI",
                relation_type="IS_PART_OF",
                source_type="LLM",
                confidence=0.8,
            ),
            ConceptRelationSyncDTO(
                pg_id=3,
                source_concept_code="AI",
                target_concept_code="ROBOT",
                relation_type="IS_DOWNSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
            ConceptRelationSyncDTO(
                pg_id=4,
                source_concept_code="ROBOT",
                target_concept_code="AUTO",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=0.9,
            ),
        ]

    @pytest.mark.asyncio
    async def test_merge_concept_relations(self, repository: Neo4jGraphRepository, sample_concept_relations):
        """测试合并概念关系。"""
        # 确保约束存在
        await repository.ensure_constraints()

        # 合并关系
        result = await repository.merge_concept_relations(
            relations=sample_concept_relations, batch_size=2
        )

        assert isinstance(result, SyncResult)
        assert result.total == 4
        assert result.success == 4
        assert result.failed == 0
        assert result.duration_ms > 0

        # 验证幂等性：再次合并相同关系
        result2 = await repository.merge_concept_relations(
            relations=sample_concept_relations, batch_size=2
        )
        assert result2.total == 4
        assert result2.success == 4  # MERGE 保证幂等性

    @pytest.mark.asyncio
    async def test_delete_all_concept_inter_relationships(self, repository: Neo4jGraphRepository, sample_concept_relations):
        """测试删除所有概念间关系。"""
        await repository.ensure_constraints()
        await repository.merge_concept_relations(sample_concept_relations)

        # 删除概念间关系
        deleted_count = await repository.delete_all_concept_inter_relationships()
        assert deleted_count >= 4

        # 再次删除应该返回 0
        deleted_count = await repository.delete_all_concept_inter_relationships()
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_find_concept_relations(self, repository: Neo4jGraphRepository, sample_concept_relations):
        """测试查询概念关系。"""
        await repository.ensure_constraints()
        await repository.merge_concept_relations(sample_concept_relations)

        # 查询 AI 的所有关系（双向）
        relations = await repository.find_concept_relations("AI", direction="both")
        assert len(relations) >= 3  # TECH->AI, CHIP->AI, AI->ROBOT

        # 验证关系结构
        for relation in relations:
            assert isinstance(relation, ConceptRelationQueryDTO)
            assert relation.source_concept_code in ["TECH", "CHIP", "AI"]
            assert relation.target_concept_code in ["AI", "ROBOT"]
            assert relation.relation_type in ["IS_UPSTREAM_OF", "IS_PART_OF", "IS_DOWNSTREAM_OF"]
            assert relation.source_type in ["MANUAL", "LLM"]
            assert 0.0 <= relation.confidence <= 1.0

        # 查询出边关系
        outgoing_relations = await repository.find_concept_relations("AI", direction="outgoing")
        assert len(outgoing_relations) >= 1  # AI->ROBOT
        assert all(r.source_concept_code == "AI" for r in outgoing_relations)

        # 查询入边关系
        incoming_relations = await repository.find_concept_relations("AI", direction="incoming")
        assert len(incoming_relations) >= 2  # TECH->AI, CHIP->AI
        assert all(r.target_concept_code == "AI" for r in incoming_relations)

        # 按关系类型筛选
        upstream_relations = await repository.find_concept_relations(
            "AI", relation_types=["IS_UPSTREAM_OF"]
        )
        assert len(upstream_relations) >= 1
        assert all(r.relation_type == "IS_UPSTREAM_OF" for r in upstream_relations)

        # 查询不存在的概念
        empty_relations = await repository.find_concept_relations("NONEXISTENT")
        assert len(empty_relations) == 0

    @pytest.mark.asyncio
    async def test_find_concept_chain(self, repository: Neo4jGraphRepository, sample_concept_relations):
        """测试查询产业链路径。"""
        await repository.ensure_constraints()
        await repository.merge_concept_relations(sample_concept_relations)

        # 查询 TECH 的下游路径
        chain = await repository.find_concept_chain("TECH", direction="outgoing", max_depth=3)
        assert len(chain) >= 3  # TECH -> AI -> ROBOT -> AUTO

        # 验证节点结构
        for node in chain:
            assert isinstance(node, ConceptChainNodeDTO)
            assert node.concept_code in ["TECH", "AI", "ROBOT", "AUTO"]
            assert 0 <= node.depth <= 3

        # 验证路径结构
        tech_node = next(n for n in chain if n.concept_code == "TECH")
        assert tech_node.depth == 0
        assert tech_node.relation_from_previous is None

        ai_node = next(n for n in chain if n.concept_code == "AI")
        assert ai_node.depth == 1
        assert ai_node.relation_from_previous == "IS_UPSTREAM_OF"

        # 查询上游路径
        upstream_chain = await repository.find_concept_chain("AUTO", direction="incoming", max_depth=3)
        assert len(upstream_chain) >= 3  # AUTO <- ROBOT <- AI <- TECH

        # 查询双向路径
        bidirectional_chain = await repository.find_concept_chain("AI", direction="both", max_depth=2)
        assert len(bidirectional_chain) >= 4  # 包含上下游所有节点

        # 按关系类型筛选
        upstream_only_chain = await repository.find_concept_chain(
            "TECH", direction="outgoing", relation_types=["IS_UPSTREAM_OF"]
        )
        assert len(upstream_only_chain) >= 2  # TECH -> AI -> ROBOT (只有 IS_UPSTREAM_OF)

        # 限制深度
        shallow_chain = await repository.find_concept_chain("TECH", direction="outgoing", max_depth=1)
        assert len(shallow_chain) >= 2  # TECH -> AI (深度 1)
        assert all(n.depth <= 1 for n in shallow_chain)

        # 查询不存在的概念
        empty_chain = await repository.find_concept_chain("NONEXISTENT")
        assert len(empty_chain) == 1  # 只有起点
        assert empty_chain[0].concept_code == "NONEXISTENT"
        assert empty_chain[0].depth == 0

    @pytest.mark.asyncio
    async def test_concept_relation_properties(self, repository: Neo4jGraphRepository, sample_concept_relations):
        """测试概念关系属性存储。"""
        await repository.ensure_constraints()
        await repository.merge_concept_relations(sample_concept_relations)

        # 查询关系并验证属性
        relations = await repository.find_concept_relations("AI", direction="incoming")
        
        # 查找 TECH->AI 关系
        tech_ai_relation = next(
            (r for r in relations if r.source_concept_code == "TECH" and r.target_concept_code == "AI"),
            None,
        )
        assert tech_ai_relation is not None
        assert tech_ai_relation.source_type == "MANUAL"
        assert tech_ai_relation.confidence == 1.0
        assert tech_ai_relation.pg_id == 1

        # 查找 CHIP->AI 关系
        chip_ai_relation = next(
            (r for r in relations if r.source_concept_code == "CHIP" and r.target_concept_code == "AI"),
            None,
        )
        assert chip_ai_relation is not None
        assert chip_ai_relation.source_type == "LLM"
        assert chip_ai_relation.confidence == 0.8
        assert chip_ai_relation.pg_id == 2

    @pytest.mark.asyncio
    async def test_mixed_relationship_types(self, repository: Neo4jGraphRepository):
        """测试混合关系类型处理。"""
        await repository.ensure_constraints()

        # 创建不同类型的关系
        mixed_relations = [
            ConceptRelationSyncDTO(
                pg_id=1,
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
            ConceptRelationSyncDTO(
                pg_id=2,
                source_concept_code="TECH",
                target_concept_code="CHIP",
                relation_type="COMPETES_WITH",
                source_type="LLM",
                confidence=0.7,
            ),
            ConceptRelationSyncDTO(
                pg_id=3,
                source_concept_code="AI",
                target_concept_code="CHIP",
                relation_type="ENABLER_FOR",
                source_type="MANUAL",
                confidence=0.9,
            ),
        ]

        await repository.merge_concept_relations(mixed_relations)

        # 按关系类型查询
        upstream_relations = await repository.find_concept_relations(
            "TECH", relation_types=["IS_UPSTREAM_OF"]
        )
        assert len(upstream_relations) == 1
        assert upstream_relations[0].relation_type == "IS_UPSTREAM_OF"

        compete_relations = await repository.find_concept_relations(
            "TECH", relation_types=["COMPETES_WITH"]
        )
        assert len(compete_relations) == 1
        assert compete_relations[0].relation_type == "COMPETES_WITH"

        # 查询多种关系类型
        multiple_relations = await repository.find_concept_relations(
            "TECH", relation_types=["IS_UPSTREAM_OF", "COMPETES_WITH"]
        )
        assert len(multiple_relations) == 2

    @pytest.mark.asyncio
    async def test_large_batch_processing(self, repository: Neo4jGraphRepository):
        """测试大批量处理。"""
        await repository.ensure_constraints()

        # 创建大量关系
        large_relations = []
        for i in range(100):
            relation = ConceptRelationSyncDTO(
                pg_id=i + 1,
                source_concept_code=f"CONCEPT_{i}",
                target_concept_code=f"CONCEPT_{i + 1}",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            )
            large_relations.append(relation)

        result = await repository.merge_concept_relations(large_relations, batch_size=20)
        assert result.total == 100
        assert result.success == 100
        assert result.failed == 0

        # 验证部分关系
        relations = await repository.find_concept_relations("CONCEPT_50")
        assert len(relations) >= 1

    @pytest.mark.asyncio
    async def test_chain_deduplication(self, repository: Neo4jGraphRepository):
        """测试链路遍历去重。"""
        await repository.ensure_constraints()

        # 创建有环路的图
        cyclic_relations = [
            ConceptRelationSyncDTO(
                pg_id=1,
                source_concept_code="A",
                target_concept_code="B",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
            ConceptRelationSyncDTO(
                pg_id=2,
                source_concept_code="B",
                target_concept_code="C",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
            ConceptRelationSyncDTO(
                pg_id=3,
                source_concept_code="C",
                target_concept_code="A",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
        ]

        await repository.merge_concept_relations(cyclic_relations)

        # 查询链路，应该去重
        chain = await repository.find_concept_chain("A", direction="outgoing", max_depth=5)
        
        # 验证去重：同一深度的同一概念只出现一次
        depth_nodes = {}
        for node in chain:
            depth = node.depth
            concept = node.concept_code
            if depth in depth_nodes:
                assert depth_nodes[depth] != concept, f"深度 {depth} 出现重复概念 {concept}"
            depth_nodes[depth] = concept

    @pytest.mark.asyncio
    async def test_error_handling(self, repository: Neo4jGraphRepository):
        """测试错误处理。"""
        await repository.ensure_constraints()

        # 测试空列表
        result = await repository.merge_concept_relations([])
        assert result.total == 0
        assert result.success == 0

        # 测试无效的关系数据（缺少必填字段）
        invalid_relations = [
            ConceptRelationSyncDTO(
                pg_id=1,
                source_concept_code="",  # 空字符串
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                source_type="MANUAL",
                confidence=1.0,
            ),
        ]

        result = await repository.merge_concept_relations(invalid_relations)
        # 应该处理错误而不崩溃
        assert result.total == 1
        assert result.failed >= 0
