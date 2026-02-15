from datetime import date

from pydantic import BaseModel

from src.modules.market_insight.domain.dtos.sentiment_dtos import (
    BrokenBoardAnalysis,
    ConsecutiveBoardLadder,
    PreviousLimitUpPerformance,
)


class SentimentMetricsDTO(BaseModel):
    """市场情绪指标汇总 DTO（应用层）"""
    
    trade_date: date
    consecutive_board_ladder: ConsecutiveBoardLadder
    previous_limit_up_performance: PreviousLimitUpPerformance
    broken_board_analysis: BrokenBoardAnalysis
