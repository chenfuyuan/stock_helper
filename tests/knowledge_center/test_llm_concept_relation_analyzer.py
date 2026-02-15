"""
LLM 概念关系分析器单元测试。

测试 prompt 构建和输出解析逻辑，使用 mock LLMService。
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.knowledge_center.domain.dtos.concept_relation_analyzer_dtos import (
    ConceptForAnalysis,
    SuggestedRelation,
)
from src.modules.knowledge_center.infrastructure.adapters.llm_concept_relation_analyzer import (
    LLMConceptRelationAnalyzer,
)


class TestLLMConceptRelationAnalyzer:
    """LLM 概念关系分析器测试类。"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM Service。"""
        service = AsyncMock()
        return service

    @pytest.fixture
    def analyzer(self, mock_llm_service):
        """创建分析器实例。"""
        return LLMConceptRelationAnalyzer(mock_llm_service)

    @pytest.fixture
    def sample_concepts(self):
        """示例概念列表。"""
        return [
            ConceptForAnalysis(code="TECH", name="技术"),
            ConceptForAnalysis(code="AI", name="人工智能"),
            ConceptForAnalysis(code="CHIP", name="芯片"),
        ]

    def test_load_system_prompt(self, analyzer):
        """测试 system prompt 加载。"""
        from src.modules.knowledge_center.infrastructure.prompt_loader import load_system_prompt
        
        system_message = load_system_prompt()

        assert "产业链分析专家" in system_message
        assert "IS_UPSTREAM_OF" in system_message
        assert "IS_DOWNSTREAM_OF" in system_message
        assert "COMPETES_WITH" in system_message
        assert "IS_PART_OF" in system_message
        assert "ENABLER_FOR" in system_message
        assert "JSON 对象" in system_message
        assert "置信度" in system_message

    def test_load_user_prompt_template(self, analyzer):
        """测试 user prompt 模板加载。"""
        from src.modules.knowledge_center.infrastructure.prompt_loader import (
            load_user_prompt_template,
            fill_user_prompt,
        )
        
        template = load_user_prompt_template()
        concepts_list = "- TECH: 技术\n- AI: 人工智能\n- CHIP: 芯片"
        prompt = fill_user_prompt(template, concepts_list)

        assert "TECH: 技术" in prompt
        assert "AI: 人工智能" in prompt
        assert "CHIP: 芯片" in prompt
        assert "IS_UPSTREAM_OF" in prompt
        assert "IS_DOWNSTREAM_OF" in prompt
        assert "COMPETES_WITH" in prompt
        assert "IS_PART_OF" in prompt
        assert "ENABLER_FOR" in prompt
        assert '"relations"' in prompt
        assert "source" in prompt
        assert "target" in prompt
        assert "type" in prompt
        assert "confidence" in prompt
        assert "reasoning" in prompt

    def test_convert_to_domain_relations(self, analyzer, sample_concepts):
        """测试将 DTO 关系转换为领域模型关系。"""
        from src.modules.knowledge_center.domain.dtos.concept_relation_analysis_dtos import (
            SuggestedRelationDTO,
        )
        
        dto_relations = [
            SuggestedRelationDTO(
                source="TECH",
                target="AI",
                type="IS_UPSTREAM_OF",
                confidence=0.8,
                reasoning="技术是人工智能的基础"
            ),
            SuggestedRelationDTO(
                source="CHIP",
                target="AI",
                type="IS_PART_OF",
                confidence=0.9,
                reasoning="芯片是人工智能的组成部分"
            ),
        ]

        relations = analyzer._convert_to_domain_relations(dto_relations, sample_concepts)

        assert len(relations) == 2
        assert relations[0].source_concept_code == "TECH"
        assert relations[0].target_concept_code == "AI"
        assert relations[0].relation_type == "IS_UPSTREAM_OF"
        assert relations[0].confidence == 0.8
        assert relations[0].reasoning == "技术是人工智能的基础"

        assert relations[1].source_concept_code == "CHIP"
        assert relations[1].target_concept_code == "AI"
        assert relations[1].relation_type == "IS_PART_OF"
        assert relations[1].confidence == 0.9
        assert relations[1].reasoning == "芯片是人工智能的组成部分"

    def test_convert_to_domain_relations_invalid_concept(self, analyzer, sample_concepts):
        """测试转换包含无效概念代码的关系。"""
        from src.modules.knowledge_center.domain.dtos.concept_relation_analysis_dtos import (
            SuggestedRelationDTO,
        )
        
        dto_relations = [
            SuggestedRelationDTO(
                source="INVALID",
                target="AI",
                type="IS_UPSTREAM_OF",
                confidence=0.8,
                reasoning="无效概念"
            ),
            SuggestedRelationDTO(
                source="TECH",
                target="AI",
                type="IS_UPSTREAM_OF",
                confidence=0.9,
                reasoning="有效关系"
            ),
        ]

        relations = analyzer._convert_to_domain_relations(dto_relations, sample_concepts)

        assert len(relations) == 1  # 只保留有效关系
        assert relations[0].source_concept_code == "TECH"
        assert relations[0].target_concept_code == "AI"

    def test_convert_to_domain_relations_duplicate_relations(self, analyzer, sample_concepts):
        """测试转换重复关系。"""
        from src.modules.knowledge_center.domain.dtos.concept_relation_analysis_dtos import (
            SuggestedRelationDTO,
        )
        
        dto_relations = [
            SuggestedRelationDTO(
                source="TECH",
                target="AI",
                type="IS_UPSTREAM_OF",
                confidence=0.8,
                reasoning="第一个"
            ),
            SuggestedRelationDTO(
                source="TECH",
                target="AI",
                type="IS_UPSTREAM_OF",
                confidence=0.9,
                reasoning="重复"
            ),
        ]

        relations = analyzer._convert_to_domain_relations(dto_relations, sample_concepts)

        assert len(relations) == 1  # 去重
        assert relations[0].source_concept_code == "TECH"
        assert relations[0].target_concept_code == "AI"
        assert relations[0].relation_type == "IS_UPSTREAM_OF"

    @pytest.mark.asyncio
    async def test_analyze_relations_success(self, analyzer, mock_llm_service, sample_concepts):
        """测试成功分析概念关系。"""
        # Mock LLM 返回
        mock_output = """
        {
          "relations": [
            {
              "source": "TECH",
              "target": "AI",
              "type": "IS_UPSTREAM_OF",
              "confidence": 0.8,
              "reasoning": "技术是人工智能的基础"
            }
          ]
        }
        """
        mock_llm_service.generate.return_value = mock_output

        relations = await analyzer.analyze_relations(sample_concepts)

        assert len(relations) == 1
        assert relations[0].source_concept_code == "TECH"
        assert relations[0].target_concept_code == "AI"
        assert relations[0].relation_type == "IS_UPSTREAM_OF"
        assert relations[0].confidence == 0.8
        assert relations[0].reasoning == "技术是人工智能的基础"

        # 验证 LLM 调用
        mock_llm_service.generate.assert_called_once()
        call_args = mock_llm_service.generate.call_args
        assert call_args.kwargs["temperature"] == 0.3
        assert "system_message" in call_args.kwargs
        assert "prompt" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_analyze_relations_insufficient_concepts(self, analyzer, mock_llm_service):
        """测试概念数量不足的情况。"""
        # 空列表
        relations = await analyzer.analyze_relations([])
        assert len(relations) == 0
        mock_llm_service.generate.assert_not_called()

        # 只有一个概念
        single_concept = [ConceptForAnalysis(code="TECH", name="技术")]
        relations = await analyzer.analyze_relations(single_concept)
        assert len(relations) == 0
        mock_llm_service.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_relations_llm_error(self, analyzer, mock_llm_service, sample_concepts):
        """测试 LLM 调用失败的情况。"""
        mock_llm_service.generate.side_effect = Exception("LLM error")

        relations = await analyzer.analyze_relations(sample_concepts)

        assert len(relations) == 0  # 降级返回空列表
        mock_llm_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_relations_invalid_llm_output(self, analyzer, mock_llm_service, sample_concepts):
        """测试 LLM 返回无效输出的情况。"""
        mock_llm_service.generate.return_value = "这不是有效的 JSON"

        relations = await analyzer.analyze_relations(sample_concepts)

        assert len(relations) == 0  # 解析失败返回空列表
        mock_llm_service.generate.assert_called_once()
