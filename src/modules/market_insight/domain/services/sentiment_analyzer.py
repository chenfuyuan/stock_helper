from collections import defaultdict

from src.modules.market_insight.domain.dtos.sentiment_dtos import (
    BoardTier,
    BrokenBoardAnalysis,
    BrokenBoardItemDTO,
    ConsecutiveBoardLadder,
    LimitUpPoolItemDTO,
    PreviousLimitUpItemDTO,
    PreviousLimitUpPerformance,
)


class SentimentAnalyzer:
    """
    市场情绪分析器（领域服务）
    纯函数式计算，不依赖外部 I/O
    """

    def analyze_consecutive_board_ladder(
        self, limit_up_pool: list[LimitUpPoolItemDTO]
    ) -> ConsecutiveBoardLadder:
        """
        分析连板梯队分布
        
        Args:
            limit_up_pool: 涨停池数据
            
        Returns:
            ConsecutiveBoardLadder: 连板梯队分布分析结果
        """
        if not limit_up_pool:
            return ConsecutiveBoardLadder(max_height=0, tiers=[], total_limit_up_count=0)

        # 按连板数分组
        board_groups: dict[int, list[str]] = defaultdict(list)
        for stock in limit_up_pool:
            board_groups[stock.consecutive_boards].append(stock.stock_name)

        # 转换为 BoardTier 并按连板数降序排列
        tiers = [
            BoardTier(board_count=board_count, stocks=stocks)
            for board_count, stocks in sorted(board_groups.items(), reverse=True)
        ]

        max_height = max(board_groups.keys())
        total_limit_up_count = len(limit_up_pool)

        return ConsecutiveBoardLadder(
            max_height=max_height, tiers=tiers, total_limit_up_count=total_limit_up_count
        )

    def analyze_previous_limit_up_performance(
        self, previous_limit_up: list[PreviousLimitUpItemDTO]
    ) -> PreviousLimitUpPerformance:
        """
        分析昨日涨停今日表现
        
        Args:
            previous_limit_up: 昨日涨停今日表现数据
            
        Returns:
            PreviousLimitUpPerformance: 昨日涨停表现分析结果
        """
        if not previous_limit_up:
            return PreviousLimitUpPerformance(
                total_count=0,
                up_count=0,
                down_count=0,
                avg_pct_chg=0.0,
                profit_rate=0.0,
                strongest=[],
                weakest=[],
            )

        total_count = len(previous_limit_up)
        up_count = sum(1 for stock in previous_limit_up if stock.pct_chg > 0)
        down_count = sum(1 for stock in previous_limit_up if stock.pct_chg < 0)

        avg_pct_chg = sum(stock.pct_chg for stock in previous_limit_up) / total_count
        profit_rate = (up_count / total_count) * 100 if total_count > 0 else 0.0

        # 按涨跌幅排序，取前 5
        sorted_by_pct_chg = sorted(previous_limit_up, key=lambda x: x.pct_chg, reverse=True)
        strongest = sorted_by_pct_chg[:5]
        weakest = sorted_by_pct_chg[-5:][::-1]  # 倒序取最后 5 个再反转

        return PreviousLimitUpPerformance(
            total_count=total_count,
            up_count=up_count,
            down_count=down_count,
            avg_pct_chg=avg_pct_chg,
            profit_rate=profit_rate,
            strongest=strongest,
            weakest=weakest,
        )

    def analyze_broken_board(
        self,
        limit_up_pool: list[LimitUpPoolItemDTO],
        broken_board_pool: list[BrokenBoardItemDTO],
    ) -> BrokenBoardAnalysis:
        """
        分析炸板情况
        
        Args:
            limit_up_pool: 涨停池数据
            broken_board_pool: 炸板池数据
            
        Returns:
            BrokenBoardAnalysis: 炸板分析结果
        """
        broken_count = len(broken_board_pool)
        total_attempted = len(limit_up_pool) + broken_count

        if total_attempted == 0:
            broken_rate = 0.0
        else:
            broken_rate = (broken_count / total_attempted) * 100

        return BrokenBoardAnalysis(
            broken_count=broken_count,
            total_attempted=total_attempted,
            broken_rate=broken_rate,
            broken_stocks=broken_board_pool,
        )
