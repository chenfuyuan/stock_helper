from datetime import date

from src.modules.market_insight.application.dtos.sentiment_metrics_dtos import (
    SentimentMetricsDTO,
)
from src.modules.market_insight.domain.ports.sentiment_data_port import ISentimentDataPort
from src.modules.market_insight.domain.services.sentiment_analyzer import SentimentAnalyzer
from src.shared.application.use_cases import BaseUseCase


class GetSentimentMetricsQuery(BaseUseCase):
    """
    获取市场情绪指标查询用例
    聚合涨停池、炸板池、昨日涨停数据，通过领域服务分析后返回
    """

    def __init__(
        self, sentiment_data_port: ISentimentDataPort, sentiment_analyzer: SentimentAnalyzer
    ):
        self.sentiment_data_port = sentiment_data_port
        self.sentiment_analyzer = sentiment_analyzer

    async def execute(self, trade_date: date) -> SentimentMetricsDTO:
        """
        执行查询
        
        Args:
            trade_date: 交易日期
            
        Returns:
            SentimentMetricsDTO: 市场情绪指标汇总
        """
        # 获取原始数据
        limit_up_pool = await self.sentiment_data_port.get_limit_up_pool(trade_date)
        broken_board_pool = await self.sentiment_data_port.get_broken_board_pool(trade_date)
        previous_limit_up = await self.sentiment_data_port.get_previous_limit_up(trade_date)

        # 通过领域服务分析
        consecutive_board_ladder = self.sentiment_analyzer.analyze_consecutive_board_ladder(
            limit_up_pool
        )
        previous_limit_up_performance = (
            self.sentiment_analyzer.analyze_previous_limit_up_performance(previous_limit_up)
        )
        broken_board_analysis = self.sentiment_analyzer.analyze_broken_board(
            limit_up_pool, broken_board_pool
        )

        return SentimentMetricsDTO(
            trade_date=trade_date,
            consecutive_board_ladder=consecutive_board_ladder,
            previous_limit_up_performance=previous_limit_up_performance,
            broken_board_analysis=broken_board_analysis,
        )
