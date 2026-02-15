"""
LLM 概念关系分析器适配器。

实现 IConceptRelationAnalyzer 接口，调用 LLM 服务分析概念间关系。
使用外部 prompt 文件和统一的 JSON 解析器。
"""

from typing import List

from loguru import logger

from src.modules.knowledge_center.domain.dtos.concept_relation_analyzer_dtos import (
    ConceptForAnalysis,
    SuggestedRelation,
)
from src.modules.knowledge_center.domain.dtos.concept_relation_analysis_dtos import (
    ConceptRelationsAnalysisResultDTO,
    normalize_relations,
)
from src.modules.knowledge_center.domain.model.enums import ConceptRelationType
from src.modules.knowledge_center.domain.ports.concept_relation_analyzer import (
    IConceptRelationAnalyzer,
)
from src.modules.knowledge_center.infrastructure.prompt_loader import (
    fill_user_prompt,
    load_system_prompt,
    load_user_prompt_template,
)
from src.shared.infrastructure.llm_json_parser import generate_and_parse
from src.modules.llm_platform.application.services.llm_service import LLMService


class LLMConceptRelationAnalyzer(IConceptRelationAnalyzer):
    """LLM 概念关系分析器适配器。"""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def analyze_relations(self, concepts: List[ConceptForAnalysis]) -> List[SuggestedRelation]:
        """
        分析给定概念列表，推荐概念间关系。
        
        基于 LLM 的产业链分析能力，识别概念间的上下游、竞争、组成等关系，
        并给出置信度和推理依据。
        
        Args:
            concepts: 待分析的概念列表（code + name）
        
        Returns:
            推荐的关系列表（含关系类型、置信度、推理依据）
        
        注意：
        - 返回的关系不包含重复（source + target + type 组合唯一）
        - 如果 LLM 输出格式异常，降级返回空列表并记录日志
        - 所有推荐关系默认为 PENDING 状态，需人工确认
        """
        if len(concepts) < 2:
            logger.warning("概念数量不足，无法进行关系分析")
            return []

        try:
            # 加载 prompt 模板
            system_message = load_system_prompt()
            user_template = load_user_prompt_template()
            
            if not system_message or not user_template:
                logger.error("Prompt 模板加载失败，请检查 prompt 文件")
                return []

            # 构建用户提示
            concepts_list = "\n".join([f"- {c.code}: {c.name}" for c in concepts])
            user_prompt = fill_user_prompt(user_template, concepts_list)

            # 调用 LLM 并解析结果
            result = await generate_and_parse(
                llm_call=self._llm.generate,
                dto_type=ConceptRelationsAnalysisResultDTO,
                prompt=user_prompt,
                system_message=system_message,
                temperature=0.3,
                normalizers=[normalize_relations],
                context_label="概念关系分析器",
                max_retries=1,
            )

            # 转换为领域模型
            suggested_relations = self._convert_to_domain_relations(result.relations, concepts)
            return suggested_relations

        except Exception as e:
            logger.error(f"LLM 概念关系分析失败: {str(e)}")
            logger.exception("LLM 概念关系分析异常详情")
            return []

    def _convert_to_domain_relations(
        self, dto_relations: List, concepts: List[ConceptForAnalysis]
    ) -> List[SuggestedRelation]:
        """
        将 DTO 关系转换为领域模型关系。
        
        Args:
            dto_relations: DTO 关系列表
            concepts: 输入的概念列表（用于验证）
        
        Returns:
            领域模型关系列表
        """
        valid_codes = {c.code for c in concepts}
        suggested_relations = []
        seen = set()  # 去重：(source, target, type)

        for rel_dto in dto_relations:
            try:
                source = rel_dto.source
                target = rel_dto.target
                rel_type = rel_dto.type
                confidence = rel_dto.confidence
                reasoning = rel_dto.reasoning

                # 验证概念代码有效性
                if source not in valid_codes or target not in valid_codes:
                    logger.warning(
                        f"跳过无效关系（概念代码不在输入列表中）: {source} -> {target}"
                    )
                    continue

                # 验证关系类型
                if rel_type not in [rt.value for rt in ConceptRelationType]:
                    logger.warning(f"跳过无效关系（关系类型未知）: {rel_type}")
                    continue

                # 验证置信度范围（DTO 已验证，但双重检查）
                if not (0.0 <= confidence <= 1.0):
                    logger.warning(f"跳过无效关系（置信度超出范围）: {confidence}")
                    continue

                # 去重
                key = (source, target, rel_type)
                if key in seen:
                    continue
                seen.add(key)

                suggested_relations.append(
                    SuggestedRelation(
                        source_concept_code=source,
                        target_concept_code=target,
                        relation_type=rel_type,
                        confidence=confidence,
                        reasoning=reasoning,
                    )
                )

            except Exception as e:
                logger.warning(f"转换关系失败: {rel_dto}, 错误: {str(e)}")
                continue

        logger.info(f"成功转换 {len(suggested_relations)} 条推荐关系")
        return suggested_relations
