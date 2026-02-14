"""
Data Engineering Adapter。

从 data_engineering 模块读取股票基础信息与财务数据，转换为 knowledge_center 的 StockGraphSyncDTO。
"""

from datetime import date, timedelta
from typing import Optional

from loguru import logger

from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    GetFinanceForTickerUseCase,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import StockGraphSyncDTO


def _enum_or_str_value(value: object) -> str | None:
    """兼容枚举与字符串两种输入，统一返回字符串值。"""
    if value is None:
        return None
    return getattr(value, "value", value)


def _date_to_yyyymmdd(value: date | None) -> str | None:
    """将日期转换为 YYYYMMDD 格式字符串。"""
    if value is None:
        return None
    return value.strftime("%Y%m%d")


class DataEngineeringAdapter:
    """
    Data Engineering 适配器。
    
    通过 data_engineering 的 Application 层 UseCase 获取数据，
    转换为 knowledge_center 模块的 StockGraphSyncDTO，
    避免直接依赖 data_engineering 的 Domain 实体。
    """

    def __init__(
        self,
        stock_repo: IStockBasicRepository,
        get_finance_use_case: Optional[GetFinanceForTickerUseCase] = None,
    ):
        """
        初始化 Data Engineering Adapter。
        
        Args:
            stock_repo: 股票仓储，用于批量查询股票列表
            get_finance_use_case: 财务数据查询用例（可选，用于获取财务快照）
        """
        self._stock_repo = stock_repo
        self._get_finance_use_case = get_finance_use_case

    async def fetch_all_stocks_for_sync(
        self,
        include_finance: bool = False,
        skip: int = 0,
        limit: int = 10000,
    ) -> list[StockGraphSyncDTO]:
        """
        获取所有股票数据并转换为同步 DTO。
        
        Args:
            include_finance: 是否包含最新一期财务快照
            skip: 跳过前 N 条记录
            limit: 查询数量上限
        
        Returns:
            StockGraphSyncDTO 列表
        """
        # 1. 从 stock_repo 获取股票基础信息
        stocks = await self._stock_repo.get_all(skip=skip, limit=limit)
        
        if not stocks:
            logger.warning(f"未找到股票数据 (skip={skip}, limit={limit})")
            return []
        
        logger.info(f"从 data_engineering 获取到 {len(stocks)} 条股票数据")
        
        # 2. 转换为 StockGraphSyncDTO
        sync_dtos: list[StockGraphSyncDTO] = []
        for stock in stocks:
            # 基础字段映射
            dto_dict = {
                "third_code": stock.third_code,
                "symbol": stock.symbol,
                "name": stock.name,
                "fullname": stock.fullname,
                "list_date": _date_to_yyyymmdd(stock.list_date),
                "list_status": _enum_or_str_value(stock.list_status),
                "curr_type": stock.curr_type,
                "industry": stock.industry,
                "area": stock.area,
                "market": _enum_or_str_value(stock.market),
                "exchange": _enum_or_str_value(stock.exchange),
            }
            
            # 3. 可选：获取最新财务快照
            if include_finance and self._get_finance_use_case:
                try:
                    finances = await self._get_finance_use_case.execute(
                        ticker=stock.third_code,
                        limit=1,
                    )
                    if finances:
                        latest = finances[0]
                        dto_dict.update({
                            "roe": latest.roe_waa,
                            "roa": getattr(latest, "roa", None),
                            "gross_margin": latest.gross_margin,
                            "debt_to_assets": latest.debt_to_assets,
                            "pe_ttm": None,  # 财务指标中无 pe_ttm，需从估值日线获取
                            "pb": None,  # 财务指标中无 pb，需从估值日线获取
                            "total_mv": None,  # 财务指标中无 total_mv，需从估值日线获取
                        })
                except Exception as e:
                    logger.warning(f"获取 {stock.third_code} 财务数据失败: {str(e)}")
                    # 财务数据获取失败不影响基础同步，继续处理
            
            sync_dtos.append(StockGraphSyncDTO(**dto_dict))
        
        logger.info(f"成功转换 {len(sync_dtos)} 条 StockGraphSyncDTO")
        return sync_dtos

    async def fetch_stocks_by_codes(
        self,
        third_codes: list[str],
        include_finance: bool = False,
    ) -> list[StockGraphSyncDTO]:
        """
        按股票代码列表获取数据并转换为同步 DTO（增量同步）。
        
        Args:
            third_codes: 股票代码列表
            include_finance: 是否包含最新一期财务快照
        
        Returns:
            StockGraphSyncDTO 列表
        """
        if not third_codes:
            return []
        
        # 1. 批量查询股票基础信息
        stocks = await self._stock_repo.get_by_third_codes(third_codes)
        
        if not stocks:
            logger.warning(f"未找到指定股票数据: {third_codes}")
            return []
        
        logger.info(f"从 data_engineering 获取到 {len(stocks)} 条指定股票数据")
        
        # 2. 转换逻辑同 fetch_all_stocks_for_sync
        sync_dtos: list[StockGraphSyncDTO] = []
        for stock in stocks:
            dto_dict = {
                "third_code": stock.third_code,
                "symbol": stock.symbol,
                "name": stock.name,
                "fullname": stock.fullname,
                "list_date": _date_to_yyyymmdd(stock.list_date),
                "list_status": _enum_or_str_value(stock.list_status),
                "curr_type": stock.curr_type,
                "industry": stock.industry,
                "area": stock.area,
                "market": _enum_or_str_value(stock.market),
                "exchange": _enum_or_str_value(stock.exchange),
            }
            
            if include_finance and self._get_finance_use_case:
                try:
                    finances = await self._get_finance_use_case.execute(
                        ticker=stock.third_code,
                        limit=1,
                    )
                    if finances:
                        latest = finances[0]
                        dto_dict.update({
                            "roe": latest.roe_waa,
                            "roa": getattr(latest, "roa", None),
                            "gross_margin": latest.gross_margin,
                            "debt_to_assets": latest.debt_to_assets,
                            "pe_ttm": None,
                            "pb": None,
                            "total_mv": None,
                        })
                except Exception as e:
                    logger.warning(f"获取 {stock.third_code} 财务数据失败: {str(e)}")
            
            sync_dtos.append(StockGraphSyncDTO(**dto_dict))
        
        logger.info(f"成功转换 {len(sync_dtos)} 条 StockGraphSyncDTO（增量）")
        return sync_dtos

    async def fetch_stocks_for_incremental_sync(
        self,
        third_codes: list[str] | None,
        include_finance: bool = False,
        window_days: int = 3,
        limit: int = 10000,
    ) -> list[StockGraphSyncDTO]:
        """
        获取增量同步数据。

        优先使用显式传入的 third_codes；若未传入，则按时间窗口自动确定同步范围。

        Args:
            third_codes: 显式指定的股票代码列表
            include_finance: 是否包含最新一期财务快照
            window_days: 时间窗口天数
            limit: 自动模式下扫描上限

        Returns:
            增量同步 DTO 列表
        """
        if third_codes:
            logger.info(f"增量同步使用显式 third_codes，数量={len(third_codes)}")
            return await self.fetch_stocks_by_codes(
                third_codes=third_codes,
                include_finance=include_finance,
            )

        threshold_date = date.today() - timedelta(days=window_days)
        logger.info(
            f"增量同步未提供 third_codes，按时间窗口自动选股: window_days={window_days}, threshold={threshold_date}"  # noqa: E501
        )

        stocks = await self._stock_repo.get_all(skip=0, limit=limit)
        candidate_codes = [
            stock.third_code
            for stock in stocks
            if stock.last_finance_sync_date is None or stock.last_finance_sync_date >= threshold_date
        ]

        if not candidate_codes:
            logger.warning("时间窗口内未找到可增量同步的股票")
            return []

        logger.info(f"时间窗口自动选出 {len(candidate_codes)} 只股票用于增量同步")
        return await self.fetch_stocks_by_codes(
            third_codes=candidate_codes,
            include_finance=include_finance,
        )
