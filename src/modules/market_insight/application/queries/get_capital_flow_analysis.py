from datetime import date

from src.modules.market_insight.application.dtos.capital_flow_analysis_dtos import (
    CapitalFlowAnalysisDTO,
)
from src.modules.market_insight.domain.ports.capital_flow_data_port import ICapitalFlowDataPort
from src.modules.market_insight.domain.services.capital_flow_analyzer import (
    CapitalFlowAnalyzer,
)
from src.shared.application.use_cases import BaseUseCase


class GetCapitalFlowAnalysisQuery(BaseUseCase):
    """
    获取资金流向分析查询用例
    聚合龙虎榜、板块资金流向数据，通过领域服务分析后返回
    """

    def __init__(
        self,
        capital_flow_data_port: ICapitalFlowDataPort,
        capital_flow_analyzer: CapitalFlowAnalyzer,
    ):
        self.capital_flow_data_port = capital_flow_data_port
        self.capital_flow_analyzer = capital_flow_analyzer

    async def execute(
        self, trade_date: date, sector_type: str | None = None
    ) -> CapitalFlowAnalysisDTO:
        """
        执行查询
        
        Args:
            trade_date: 交易日期
            sector_type: 板块类型（可选）
            
        Returns:
            CapitalFlowAnalysisDTO: 资金流向分析汇总
        """
        # 获取原始数据
        dragon_tiger = await self.capital_flow_data_port.get_dragon_tiger(trade_date)
        sector_capital_flow = await self.capital_flow_data_port.get_sector_capital_flow(
            trade_date, sector_type
        )

        # 通过领域服务分析
        dragon_tiger_analysis = self.capital_flow_analyzer.analyze_dragon_tiger(dragon_tiger)
        sector_capital_flow_analysis = self.capital_flow_analyzer.analyze_sector_capital_flow(
            sector_capital_flow
        )

        return CapitalFlowAnalysisDTO(
            trade_date=trade_date,
            dragon_tiger_analysis=dragon_tiger_analysis,
            sector_capital_flow_analysis=sector_capital_flow_analysis,
        )
