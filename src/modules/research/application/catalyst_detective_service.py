import logging
from typing import List

from src.shared.domain.exceptions import BadRequestException
from src.modules.research.domain.ports.catalyst_data import ICatalystDataPort
from src.modules.research.domain.ports.catalyst_context_builder import (
    ICatalystContextBuilder,
)
from src.modules.research.domain.ports.catalyst_detective_agent import (
    ICatalystDetectiveAgentPort,
)
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystStockOverview,
    CatalystSearchResult,
)
from src.modules.research.domain.dtos.catalyst_context import CatalystContextDTO
from src.modules.research.domain.dtos.catalyst_dtos import (
    CatalystDetectiveAgentResult,
)
from src.modules.research.domain.exceptions import (
    StockNotFoundError,
    CatalystSearchError,
    LLMOutputParseError,
)

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

    async def run(self, symbol: str) -> CatalystDetectiveAgentResult:
        """
        执行催化剂侦探全流程

        :param symbol: 股票代码
        :return: 催化剂分析结果 (含解析后的 result 和原始 llm_output)
        :raises BadRequestException: 参数错误
        :raises StockNotFoundError: 标的不存在
        :raises CatalystSearchError: 搜索失败
        :raises LLMOutputParseError: LLM 解析失败
        """
        if not symbol:
            raise BadRequestException(message="Symbol cannot be empty")

        # 1. 获取股票概览
        # ICatalystDataPort.get_stock_overview returns Optional[CatalystStockOverview]
        overview = await self.data_port.get_stock_overview(symbol)

        if not overview:
            logger.warning(f"Catalyst Detective: Stock not found for symbol {symbol}")
            raise StockNotFoundError(symbol)

        # 2. 从Web搜索获取催化剂上下文
        # ICatalystDataPort.search_catalyst_context returns List[CatalystSearchResult]
        search_results: List[CatalystSearchResult] = (
            await self.data_port.search_catalyst_context(
                overview.stock_name, overview.industry
            )
        )

        # 3. 校验搜索结果是否全为空
        # Check if all dimensions have empty items
        all_empty = all(not r.items for r in search_results)
        if all_empty:
            logger.warning(f"All catalyst search dimensions returned empty for {symbol}")
            raise CatalystSearchError(message="虽然找到了标的，但关于该标的的催化剂搜索全部失败或无结果，无法分析。")

        # 4. 构建上下文 (Infrastructure implementation handles formatting)
        context_dto: CatalystContextDTO = self.context_builder.build(
            overview, search_results
        )

        # 5. 调用 Agent 进行分析
        agent_result: CatalystDetectiveAgentResult = await self.agent_port.analyze(
            symbol, context_dto
        )

        return agent_result
