import logging
from typing import Any, List

from src.modules.research.domain.dtos.catalyst_context import (
    CatalystContextDTO,
)
from src.modules.research.domain.dtos.catalyst_dtos import (
    CatalystDetectiveAgentResult,
)
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
)
from src.modules.research.domain.ports.catalyst_context_builder import (
    ICatalystContextBuilder,
)
from src.modules.research.domain.ports.catalyst_data import ICatalystDataPort
from src.modules.research.domain.ports.catalyst_detective_agent import (
    ICatalystDetectiveAgentPort,
)
from src.shared.domain.exceptions import BadRequestException

logger = logging.getLogger(__name__)


class CatalystDetectiveService:
    def __init__(
        self,
        data_port: ICatalystDataPort,
        context_builder: ICatalystContextBuilder,
        agent_port: ICatalystDetectiveAgentPort,
    ):
        self.data_port = data_port
        self.context_builder = context_builder
        self.agent_port = agent_port

    async def run(self, symbol: str) -> dict[str, Any]:
        """
        执行催化剂侦探全流程，返回与其他专家一致的 dict[str, Any]。

        :param symbol: 股票代码
        :return: 归一化后的结果字典（result、raw_llm_output、user_prompt、catalyst_context）
        :raises BadRequestException: 参数错误、标的不存在、搜索全部失败等
        """
        if not symbol:
            raise BadRequestException(message="symbol 为必填")

        # 1. 获取股票概览
        overview = await self.data_port.get_stock_overview(symbol)
        if not overview:
            logger.warning("催化剂侦探：标的不存在，symbol=%s", symbol)
            raise BadRequestException(
                message=f"标的不存在或无法获取概览：{symbol}"
            )

        # 2. 从 Web 搜索获取催化剂上下文
        search_results: List[CatalystSearchResult] = (
            await self.data_port.search_catalyst_context(
                overview.stock_name, overview.industry
            )
        )

        # 3. 校验搜索结果是否全为空
        all_empty = all(not r.items for r in search_results)
        if all_empty:
            logger.warning(
                "催化剂侦探：四维度搜索全部无结果，symbol=%s", symbol
            )
            raise BadRequestException(
                message="虽然找到了标的，但关于该标的的催化剂搜索全部失败或无结果，无法分析。"
            )

        # 4. 构建上下文
        context_dto: CatalystContextDTO = self.context_builder.build(
            overview, search_results
        )

        # 5. 调用 Agent 进行分析
        agent_result: CatalystDetectiveAgentResult = (
            await self.agent_port.analyze(symbol, context_dto)
        )

        # 6. 归一化为 dict，与其他专家返回类型一致
        result_dto = agent_result.result
        return {
            "result": result_dto.model_dump(),
            "narrative_report": result_dto.narrative_report,
            "raw_llm_output": agent_result.raw_llm_output,
            "user_prompt": agent_result.user_prompt,
            "catalyst_context": agent_result.catalyst_context.model_dump(),
        }
