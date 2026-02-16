"""板块资金流向数据同步 Command。"""

from datetime import date

from loguru import logger

from src.modules.data_engineering.domain.model.sector_capital_flow import SectorCapitalFlow
from src.modules.data_engineering.domain.ports.providers.sector_capital_flow_provider import (
    ISectorCapitalFlowProvider,
)
from src.modules.data_engineering.domain.ports.repositories.sector_capital_flow_repo import (
    ISectorCapitalFlowRepository,
)


class SyncSectorCapitalFlowCmd:
    """
    同步板块资金流向数据命令。
    
    从 AkShare 获取板块资金流向数据并写入 PostgreSQL。
    """

    def __init__(
        self,
        capital_flow_provider: ISectorCapitalFlowProvider,
        sector_capital_flow_repo: ISectorCapitalFlowRepository,
    ):
        self.capital_flow_provider = capital_flow_provider
        self.sector_capital_flow_repo = sector_capital_flow_repo

    async def execute(self, trade_date: date) -> int:
        """
        执行板块资金流向数据同步。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            同步条数
            
        Raises:
            Exception: 同步失败时抛出
        """
        logger.info(f"开始同步板块资金流向数据：{trade_date}")
        
        capital_flow_dtos = await self.capital_flow_provider.fetch_sector_capital_flow()
        
        if not capital_flow_dtos:
            logger.info(f"板块资金流向数据为空：{trade_date}")
            return 0
        
        capital_flow_entities = [
            SectorCapitalFlow(
                trade_date=trade_date,
                sector_name=dto.sector_name,
                sector_type=dto.sector_type,
                net_amount=dto.net_amount,
                inflow_amount=dto.inflow_amount,
                outflow_amount=dto.outflow_amount,
                pct_chg=dto.pct_chg,
            )
            for dto in capital_flow_dtos
        ]
        
        count = await self.sector_capital_flow_repo.save_all(capital_flow_entities)
        logger.info(f"板块资金流向数据同步成功：{count} 条")
        
        return count
