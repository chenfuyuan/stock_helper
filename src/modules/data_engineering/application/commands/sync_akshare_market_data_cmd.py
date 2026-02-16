"""AkShare 市场数据同步编排 Command。"""

from datetime import date

from loguru import logger

from src.modules.data_engineering.application.commands.sync_broken_board_cmd import (
    SyncBrokenBoardCmd,
)
from src.modules.data_engineering.application.commands.sync_dragon_tiger_cmd import (
    SyncDragonTigerCmd,
)
from src.modules.data_engineering.application.commands.sync_limit_up_pool_cmd import (
    SyncLimitUpPoolCmd,
)
from src.modules.data_engineering.application.commands.sync_previous_limit_up_cmd import (
    SyncPreviousLimitUpCmd,
)
from src.modules.data_engineering.application.commands.sync_sector_capital_flow_cmd import (
    SyncSectorCapitalFlowCmd,
)
from src.modules.data_engineering.application.dtos.sync_result_dtos import AkShareSyncResult
from src.modules.data_engineering.domain.ports.providers.dragon_tiger_provider import (
    IDragonTigerProvider,
)
from src.modules.data_engineering.domain.ports.providers.market_sentiment_provider import (
    IMarketSentimentProvider,
)
from src.modules.data_engineering.domain.ports.providers.sector_capital_flow_provider import (
    ISectorCapitalFlowProvider,
)
from src.modules.data_engineering.domain.ports.repositories.broken_board_repo import (
    IBrokenBoardRepository,
)
from src.modules.data_engineering.domain.ports.repositories.dragon_tiger_repo import (
    IDragonTigerRepository,
)
from src.modules.data_engineering.domain.ports.repositories.limit_up_pool_repo import (
    ILimitUpPoolRepository,
)
from src.modules.data_engineering.domain.ports.repositories.previous_limit_up_repo import (
    IPreviousLimitUpRepository,
)
from src.modules.data_engineering.domain.ports.repositories.sector_capital_flow_repo import (
    ISectorCapitalFlowRepository,
)


class SyncAkShareMarketDataCmd:
    """
    AkShare 市场数据同步编排命令。
    
    作为编排入口，依次调用 5 个子 Command 完成数据同步，实现错误隔离：
    单个子任务失败不中断其他任务的执行。
    """

    def __init__(
        self,
        sentiment_provider: IMarketSentimentProvider,
        dragon_tiger_provider: IDragonTigerProvider,
        capital_flow_provider: ISectorCapitalFlowProvider,
        limit_up_pool_repo: ILimitUpPoolRepository,
        broken_board_repo: IBrokenBoardRepository,
        previous_limit_up_repo: IPreviousLimitUpRepository,
        dragon_tiger_repo: IDragonTigerRepository,
        sector_capital_flow_repo: ISectorCapitalFlowRepository,
    ):
        """
        初始化编排命令，构建 5 个子 Command。
        
        Args:
            sentiment_provider: 市场情绪数据提供方
            dragon_tiger_provider: 龙虎榜数据提供方
            capital_flow_provider: 板块资金流向数据提供方
            limit_up_pool_repo: 涨停池仓储
            broken_board_repo: 炸板池仓储
            previous_limit_up_repo: 昨日涨停仓储
            dragon_tiger_repo: 龙虎榜仓储
            sector_capital_flow_repo: 板块资金流向仓储
        """
        # 构建子 Command
        self.limit_up_cmd = SyncLimitUpPoolCmd(sentiment_provider, limit_up_pool_repo)
        self.broken_board_cmd = SyncBrokenBoardCmd(sentiment_provider, broken_board_repo)
        self.previous_limit_up_cmd = SyncPreviousLimitUpCmd(
            sentiment_provider, previous_limit_up_repo
        )
        self.dragon_tiger_cmd = SyncDragonTigerCmd(dragon_tiger_provider, dragon_tiger_repo)
        self.sector_capital_flow_cmd = SyncSectorCapitalFlowCmd(
            capital_flow_provider, sector_capital_flow_repo
        )

    async def execute(self, trade_date: date) -> AkShareSyncResult:
        """
        执行 AkShare 市场数据同步。
        
        依次调用 5 个子 Command，错误隔离：单个失败不中断其他。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            AkShareSyncResult: 聚合的同步结果摘要
        """
        logger.info(f"开始编排 AkShare 市场数据同步：{trade_date}")

        errors = []
        limit_up_pool_count = 0
        broken_board_count = 0
        previous_limit_up_count = 0
        dragon_tiger_count = 0
        sector_capital_flow_count = 0

        # 1. 同步涨停池数据
        try:
            limit_up_pool_count = await self.limit_up_cmd.execute(trade_date)
        except Exception as e:
            error_msg = f"涨停池数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 2. 同步炸板池数据
        try:
            broken_board_count = await self.broken_board_cmd.execute(trade_date)
        except Exception as e:
            error_msg = f"炸板池数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 3. 同步昨日涨停表现数据
        try:
            previous_limit_up_count = await self.previous_limit_up_cmd.execute(trade_date)
        except Exception as e:
            error_msg = f"昨日涨停表现数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 4. 同步龙虎榜数据
        try:
            dragon_tiger_count = await self.dragon_tiger_cmd.execute(trade_date)
        except Exception as e:
            error_msg = f"龙虎榜数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 5. 同步板块资金流向数据
        try:
            sector_capital_flow_count = await self.sector_capital_flow_cmd.execute(trade_date)
        except Exception as e:
            error_msg = f"板块资金流向数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        logger.info(
            f"AkShare 市场数据同步完成：{trade_date}，"
            f"涨停池 {limit_up_pool_count}，炸板池 {broken_board_count}，"
            f"昨日涨停 {previous_limit_up_count}，龙虎榜 {dragon_tiger_count}，"
            f"资金流向 {sector_capital_flow_count}，错误 {len(errors)}"
        )

        return AkShareSyncResult(
            trade_date=trade_date,
            limit_up_pool_count=limit_up_pool_count,
            broken_board_count=broken_board_count,
            previous_limit_up_count=previous_limit_up_count,
            dragon_tiger_count=dragon_tiger_count,
            sector_capital_flow_count=sector_capital_flow_count,
            errors=errors,
        )
