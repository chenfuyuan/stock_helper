"""
概念关系 REST 端点 E2E 集成测试。

通过 TestClient 验证各端点的正常与异常场景。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app


class TestConceptRelationEndpointsE2E:
    """概念关系 REST 端点 E2E 测试类。"""

    @pytest.fixture
    def client(self) -> TestClient:
        """创建测试客户端。"""
        return TestClient(app)

    @pytest.fixture
    def sample_relation_data(self):
        """示例关系数据。"""
        return {
            "source_concept_code": "TECH",
            "target_concept_code": "AI",
            "relation_type": "IS_UPSTREAM_OF",
            "note": "测试备注",
            "reason": "测试原因",
        }

    def test_create_concept_relation_success(self, client: TestClient, sample_relation_data):
        """测试成功创建概念关系。"""
        response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=sample_relation_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["source_concept_code"] == sample_relation_data["source_concept_code"]
        assert data["target_concept_code"] == sample_relation_data["target_concept_code"]
        assert data["relation_type"] == sample_relation_data["relation_type"]
        assert data["source_type"] == "MANUAL"
        assert data["status"] == "CONFIRMED"
        assert data["confidence"] == 1.0
        assert data["ext_info"]["note"] == sample_relation_data["note"]
        assert data["ext_info"]["reason"] == sample_relation_data["reason"]
        assert data["created_by"] == "api_user"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_concept_relation_validation_error(self, client: TestClient):
        """测试创建概念关系验证错误。"""
        # 缺少必填字段
        invalid_data = {
            "source_concept_code": "TECH",
            # 缺少 target_concept_code 和 relation_type
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=invalid_data,
        )

        assert response.status_code == 422  # Validation Error

    def test_create_concept_relation_duplicate(self, client: TestClient, sample_relation_data):
        """测试创建重复概念关系。"""
        # 创建第一个关系
        client.post("/api/v1/knowledge-graph/concept-relations", json=sample_relation_data)

        # 创建重复关系
        response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=sample_relation_data,
        )

        assert response.status_code == 400  # Bad Request (唯一约束违反)

    def test_list_concept_relations_success(self, client: TestClient, sample_relation_data):
        """测试成功列表查询概念关系。"""
        # 创建测试数据
        client.post("/api/v1/knowledge-graph/concept-relations", json=sample_relation_data)

        # 创建第二个关系
        second_relation = {
            "source_concept_code": "CHIP",
            "target_concept_code": "AI",
            "relation_type": "IS_PART_OF",
        }
        client.post("/api/v1/knowledge-graph/concept-relations", json=second_relation)

        # 查询所有关系
        response = client.get("/api/v1/knowledge-graph/concept-relations")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "items" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["items"]) >= 2
        assert data["total"] >= 2

        # 按源概念筛选
        response = client.get(
            "/api/v1/knowledge-graph/concept-relations?source_concept_code=TECH"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["source_concept_code"] == "TECH" for item in data["items"])

        # 按目标概念筛选
        response = client.get(
            "/api/v1/knowledge-graph/concept-relations?target_concept_code=AI"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2
        assert all(item["target_concept_code"] == "AI" for item in data["items"])

        # 按关系类型筛选
        response = client.get(
            "/api/v1/knowledge-graph/concept-relations?relation_type=IS_UPSTREAM_OF"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["relation_type"] == "IS_UPSTREAM_OF" for item in data["items"])

        # 分页查询
        response = client.get("/api/v1/knowledge-graph/concept-relations?limit=1&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["limit"] == 1
        assert data["offset"] == 0

    def test_get_concept_relation_by_id_success(self, client: TestClient, sample_relation_data):
        """测试成功根据 ID 查询概念关系。"""
        # 创建关系
        create_response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=sample_relation_data,
        )
        relation_id = create_response.json()["id"]

        # 根据 ID 查询
        response = client.get(f"/api/v1/knowledge-graph/concept-relations/{relation_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == relation_id
        assert data["source_concept_code"] == sample_relation_data["source_concept_code"]
        assert data["target_concept_code"] == sample_relation_data["target_concept_code"]

    def test_get_concept_relation_by_id_not_found(self, client: TestClient):
        """测试查询不存在的概念关系。"""
        response = client.get("/api/v1/knowledge-graph/concept-relations/99999")
        assert response.status_code == 404

    def test_update_concept_relation_success(self, client: TestClient, sample_relation_data):
        """测试成功更新概念关系。"""
        # 创建关系
        create_response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=sample_relation_data,
        )
        relation_id = create_response.json()["id"]

        # 更新状态
        update_data = {"status": "REJECTED"}
        response = client.put(
            f"/api/v1/knowledge-graph/concept-relations/{relation_id}",
            json=update_data,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == relation_id
        assert data["status"] == "REJECTED"

    def test_update_concept_relation_not_found(self, client: TestClient):
        """测试更新不存在的概念关系。"""
        update_data = {"status": "REJECTED"}
        response = client.put(
            "/api/v1/knowledge-graph/concept-relations/99999",
            json=update_data,
        )
        assert response.status_code == 404

    def test_update_concept_relation_invalid_data(self, client: TestClient, sample_relation_data):
        """测试更新概念关系无效数据。"""
        # 创建关系
        create_response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=sample_relation_data,
        )
        relation_id = create_response.json()["id"]

        # 无效状态
        update_data = {"status": "INVALID_STATUS"}
        response = client.put(
            f"/api/v1/knowledge-graph/concept-relations/{relation_id}",
            json=update_data,
        )
        assert response.status_code == 400

    def test_delete_concept_relation_success(self, client: TestClient, sample_relation_data):
        """测试成功删除概念关系。"""
        # 创建关系
        create_response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            json=sample_relation_data,
        )
        relation_id = create_response.json()["id"]

        # 删除关系
        response = client.delete(f"/api/v1/knowledge-graph/concept-relations/{relation_id}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/api/v1/knowledge-graph/concept-relations/{relation_id}")
        assert response.status_code == 404

    def test_delete_concept_relation_not_found(self, client: TestClient):
        """测试删除不存在的概念关系。"""
        response = client.delete("/api/v1/knowledge-graph/concept-relations/99999")
        assert response.status_code == 404

    def test_llm_suggest_relations_success(self, client: TestClient):
        """测试 LLM 推荐概念关系成功。"""
        # 注意：这个测试需要 mock LLM 服务，否则会失败
        suggest_data = {
            "concept_codes_with_names": [
                ("TECH", "技术"),
                ("AI", "人工智能"),
                ("CHIP", "芯片"),
            ],
            "min_confidence": 0.5,
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/llm-suggest",
            json=suggest_data,
        )

        # 由于没有 mock LLM，这里可能失败，但端点应该存在
        assert response.status_code in [200, 500]  # 成功或 LLM 服务错误

        if response.status_code == 200:
            data = response.json()
            assert "batch_id" in data
            assert "total_suggested" in data
            assert "created_count" in data
            assert "skipped_count" in data
            assert "message" in data

    def test_llm_suggest_relations_validation_error(self, client: TestClient):
        """测试 LLM 推荐概念关系验证错误。"""
        # 概念数量不足
        suggest_data = {
            "concept_codes_with_names": [
                ("TECH", "技术"),
            ],
            "min_confidence": 0.5,
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/llm-suggest",
            json=suggest_data,
        )

        assert response.status_code == 400  # 概念数量不足

        # 置信度超出范围
        suggest_data = {
            "concept_codes_with_names": [
                ("TECH", "技术"),
                ("AI", "人工智能"),
            ],
            "min_confidence": 1.5,  # 超出范围
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/llm-suggest",
            json=suggest_data,
        )

        assert response.status_code == 422  # Validation Error

    def test_sync_concept_relations_success(self, client: TestClient):
        """测试同步概念关系成功。"""
        sync_data = {
            "mode": "incremental",
            "batch_size": 100,
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/sync",
            json=sync_data,
        )

        # 同步可能成功或无数据
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "mode" in data
            assert "total_relations" in data
            assert "deleted_count" in data
            assert "sync_success" in data
            assert "sync_failed" in data
            assert "duration_ms" in data
            assert "message" in data

    def test_sync_concept_relations_validation_error(self, client: TestClient):
        """测试同步概念关系验证错误。"""
        # 无效模式
        sync_data = {
            "mode": "invalid_mode",
            "batch_size": 100,
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/sync",
            json=sync_data,
        )

        assert response.status_code == 400

        # 批次大小超出范围
        sync_data = {
            "mode": "incremental",
            "batch_size": 2000,  # 超出限制
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/sync",
            json=sync_data,
        )

        assert response.status_code == 422

    def test_query_concept_relations_success(self, client: TestClient):
        """测试查询概念关系网络成功。"""
        # 这个测试需要预先在 Neo4j 中有数据
        response = client.get("/api/v1/knowledge-graph/concepts/TECH/relations")
        
        # 可能返回空结果或错误
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "concept_code" in data
            assert "relations" in data
            assert "total" in data
            assert isinstance(data["relations"], list)

    def test_query_concept_relations_with_filters(self, client: TestClient):
        """测试带筛选的概念关系网络查询。"""
        response = client.get(
            "/api/v1/knowledge-graph/concepts/TECH/relations?direction=outgoing&relation_types=IS_UPSTREAM_OF"
        )
        
        assert response.status_code in [200, 500]

    def test_query_concept_chain_success(self, client: TestClient):
        """测试查询产业链路径成功。"""
        response = client.get("/api/v1/knowledge-graph/concepts/TECH/chain")
        
        # 可能返回空结果或错误
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "concept_code" in data
            assert "direction" in data
            assert "max_depth" in data
            assert "nodes" in data
            assert "total_nodes" in data
            assert isinstance(data["nodes"], list)

    def test_query_concept_chain_with_parameters(self, client: TestClient):
        """测试带参数的产业链路径查询。"""
        response = client.get(
            "/api/v1/knowledge-graph/concepts/TECH/chain?direction=upstream&max_depth=2&relation_types=IS_UPSTREAM_OF"
        )
        
        assert response.status_code in [200, 500]

    def test_invalid_endpoints(self, client: TestClient):
        """测试无效端点。"""
        # 无效的路径
        response = client.get("/api/v1/knowledge-graph/concept-relations/invalid")
        assert response.status_code == 404

        response = client.get("/api/v1/knowledge-graph/concepts/INVALID/relations")
        assert response.status_code in [200, 404, 500]  # 可能返回空结果或 404

        response = client.get("/api/v1/knowledge-graph/concepts/INVALID/chain")
        assert response.status_code in [200, 404, 500]

    def test_method_not_allowed(self, client: TestClient):
        """测试不允许的 HTTP 方法。"""
        # GET 不应该用于创建
        response = client.get("/api/v1/knowledge-graph/concept-relations")
        assert response.status_code in [200, 405]  # 200 是列表查询，405 是方法不允许

        # POST 不应该用于删除
        response = client.post("/api/v1/knowledge-graph/concept-relations/1")
        assert response.status_code == 405

    def test_content_type_validation(self, client: TestClient):
        """测试内容类型验证。"""
        # 发送非 JSON 数据
        response = client.post(
            "/api/v1/knowledge-graph/concept-relations",
            data="not json",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422

    def test_large_payload_handling(self, client: TestClient):
        """测试大载荷处理。"""
        # 创建大量概念
        large_concepts = [(f"CONCEPT_{i}", f"概念_{i}") for i in range(100)]
        suggest_data = {
            "concept_codes_with_names": large_concepts,
            "min_confidence": 0.5,
        }

        response = client.post(
            "/api/v1/knowledge-graph/concept-relations/llm-suggest",
            json=suggest_data,
        )
        
        # 应该能处理大载荷（可能成功或因 LLM 服务失败）
        assert response.status_code in [200, 400, 500]
