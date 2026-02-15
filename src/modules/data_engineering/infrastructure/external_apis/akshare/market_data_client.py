from datetime import date

import pandas as pd
from loguru import logger

from src.modules.data_engineering.domain.dtos.capital_flow_dtos import SectorCapitalFlowDTO
from src.modules.data_engineering.domain.dtos.dragon_tiger_dtos import DragonTigerDetailDTO
from src.modules.data_engineering.domain.dtos.market_sentiment_dtos import (
    BrokenBoardDTO,
    LimitUpPoolDTO,
    PreviousLimitUpDTO,
)
from src.modules.data_engineering.domain.ports.providers.dragon_tiger_provider import (
    IDragonTigerProvider,
)
from src.modules.data_engineering.domain.ports.providers.market_sentiment_provider import (
    IMarketSentimentProvider,
)
from src.modules.data_engineering.domain.ports.providers.sector_capital_flow_provider import (
    ISectorCapitalFlowProvider,
)
from src.modules.data_engineering.infrastructure.external_apis.akshare.base_client import (
    AkShareBaseClient,
)
from src.modules.data_engineering.infrastructure.external_apis.akshare.converters.stock_code_converter import (
    convert_akshare_stock_code,
)
from src.shared.domain.exceptions import AppException


class AkShareMarketDataClient(
    AkShareBaseClient, IMarketSentimentProvider, IDragonTigerProvider, ISectorCapitalFlowProvider
):
    """
    AkShare 市场数据客户端（基础设施层适配器）
    实现市场情绪、龙虎榜、资金流向三个 Provider 接口
    调用 AkShare API 获取市场增强数据
    """

    async def fetch_limit_up_pool(self, trade_date: date) -> list[LimitUpPoolDTO]:
        """
        获取指定日期的涨停池数据（含连板天数）
        调用 akshare.stock_zt_pool_em(date=<yyyymmdd>) 接口
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[LimitUpPoolDTO]: 涨停池数据列表
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            date_str = trade_date.strftime("%Y%m%d")
            logger.info(f"开始获取涨停池数据：{date_str}")
            df: pd.DataFrame = await self._rate_limited_call(ak.stock_zt_pool_em, date=date_str)

            if df is None or df.empty:
                logger.warning(f"涨停池数据为空：{date_str}")
                return []

            result: list[LimitUpPoolDTO] = []
            for _, row in df.iterrows():
                raw_code = str(row.get("代码", "")).strip()
                third_code = convert_akshare_stock_code(raw_code)
                if not third_code:
                    continue

                result.append(
                    LimitUpPoolDTO(
                        third_code=third_code,
                        stock_name=str(row.get("名称", "")),
                        pct_chg=float(row.get("涨跌幅", 0.0)),
                        close=float(row.get("最新价", 0.0)),
                        amount=float(row.get("成交额", 0.0)),
                        turnover_rate=float(row.get("换手率", 0.0)),
                        consecutive_boards=int(row.get("连板数", 1)),
                        first_limit_up_time=str(row.get("首次封板时间", "")) or None,
                        last_limit_up_time=str(row.get("最后封板时间", "")) or None,
                        industry=str(row.get("所属行业", "")),
                    )
                )

            logger.info(f"成功获取 {len(result)} 条涨停池记录：{date_str}")
            return result

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取涨停池数据失败：{date_str}，错误：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message=f"获取涨停池数据失败：{date_str}",
                details=f"stock_zt_pool_em API 调用失败: {str(e)}",
            )

    async def fetch_broken_board_pool(self, trade_date: date) -> list[BrokenBoardDTO]:
        """
        获取指定日期的炸板池数据
        调用 akshare.stock_zt_pool_zbgc_em(date=<yyyymmdd>) 接口
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[BrokenBoardDTO]: 炸板池数据列表
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            date_str = trade_date.strftime("%Y%m%d")
            logger.info(f"开始获取炸板池数据：{date_str}")
            df: pd.DataFrame = await self._rate_limited_call(
                ak.stock_zt_pool_zbgc_em, date=date_str
            )

            if df is None or df.empty:
                logger.warning(f"炸板池数据为空：{date_str}")
                return []

            result: list[BrokenBoardDTO] = []
            for _, row in df.iterrows():
                raw_code = str(row.get("代码", "")).strip()
                third_code = convert_akshare_stock_code(raw_code)
                if not third_code:
                    continue

                result.append(
                    BrokenBoardDTO(
                        third_code=third_code,
                        stock_name=str(row.get("名称", "")),
                        pct_chg=float(row.get("涨跌幅", 0.0)),
                        close=float(row.get("最新价", 0.0)),
                        amount=float(row.get("成交额", 0.0)),
                        turnover_rate=float(row.get("换手率", 0.0)),
                        open_count=int(row.get("开板次数", 0)),
                        first_limit_up_time=str(row.get("首次封板时间", "")) or None,
                        last_open_time=str(row.get("最后开板时间", "")) or None,
                        industry=str(row.get("所属行业", "")),
                    )
                )

            logger.info(f"成功获取 {len(result)} 条炸板池记录：{date_str}")
            return result

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取炸板池数据失败：{date_str}，错误：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message=f"获取炸板池数据失败：{date_str}",
                details=f"stock_zt_pool_zbgc_em API 调用失败: {str(e)}",
            )

    async def fetch_previous_limit_up(self, trade_date: date) -> list[PreviousLimitUpDTO]:
        """
        获取昨日涨停股今日表现数据
        调用 akshare.stock_zt_pool_previous_em(date=<yyyymmdd>) 接口
        
        Args:
            trade_date: 交易日期（今日日期，即表现观察日）
            
        Returns:
            list[PreviousLimitUpDTO]: 昨日涨停表现数据列表
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            date_str = trade_date.strftime("%Y%m%d")
            logger.info(f"开始获取昨日涨停表现数据：{date_str}")
            df: pd.DataFrame = await self._rate_limited_call(
                ak.stock_zt_pool_previous_em, date=date_str
            )

            if df is None or df.empty:
                logger.warning(f"昨日涨停表现数据为空：{date_str}")
                return []

            result: list[PreviousLimitUpDTO] = []
            for _, row in df.iterrows():
                raw_code = str(row.get("代码", "")).strip()
                third_code = convert_akshare_stock_code(raw_code)
                if not third_code:
                    continue

                result.append(
                    PreviousLimitUpDTO(
                        third_code=third_code,
                        stock_name=str(row.get("名称", "")),
                        pct_chg=float(row.get("涨跌幅", 0.0)),
                        close=float(row.get("最新价", 0.0)),
                        amount=float(row.get("成交额", 0.0)),
                        turnover_rate=float(row.get("换手率", 0.0)),
                        yesterday_consecutive_boards=int(row.get("昨日连板数", 1)),
                        industry=str(row.get("所属行业", "")),
                    )
                )

            logger.info(f"成功获取 {len(result)} 条昨日涨停表现记录：{date_str}")
            return result

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取昨日涨停表现数据失败：{date_str}，错误：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message=f"获取昨日涨停表现数据失败：{date_str}",
                details=f"stock_zt_pool_previous_em API 调用失败: {str(e)}",
            )

    async def fetch_dragon_tiger_detail(self, trade_date: date) -> list[DragonTigerDetailDTO]:
        """
        获取指定日期的龙虎榜详情数据
        调用 akshare.stock_lhb_detail_em(start_date=<yyyymmdd>, end_date=<yyyymmdd>) 接口
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[DragonTigerDetailDTO]: 龙虎榜详情数据列表
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            date_str = trade_date.strftime("%Y%m%d")
            logger.info(f"开始获取龙虎榜数据：{date_str}")
            df: pd.DataFrame = await self._rate_limited_call(
                ak.stock_lhb_detail_em, start_date=date_str, end_date=date_str
            )

            if df is None or df.empty:
                logger.warning(f"龙虎榜数据为空：{date_str}")
                return []

            result: list[DragonTigerDetailDTO] = []
            for _, row in df.iterrows():
                raw_code = str(row.get("代码", "")).strip()
                third_code = convert_akshare_stock_code(raw_code)
                if not third_code:
                    continue

                buy_seats = []
                sell_seats = []
                for i in range(1, 6):
                    buy_seat_name = row.get(f"买{i}席位", "")
                    buy_amt = row.get(f"买{i}金额", 0.0)
                    if buy_seat_name and buy_seat_name != "-":
                        buy_seats.append(
                            {"seat_name": str(buy_seat_name), "buy_amount": float(buy_amt)}
                        )

                    sell_seat_name = row.get(f"卖{i}席位", "")
                    sell_amt = row.get(f"卖{i}金额", 0.0)
                    if sell_seat_name and sell_seat_name != "-":
                        sell_seats.append(
                            {"seat_name": str(sell_seat_name), "sell_amount": float(sell_amt)}
                        )

                result.append(
                    DragonTigerDetailDTO(
                        third_code=third_code,
                        stock_name=str(row.get("名称", "")),
                        pct_chg=float(row.get("涨跌幅", 0.0)),
                        close=float(row.get("收盘价", 0.0)),
                        reason=str(row.get("上榜原因", "")),
                        net_amount=float(row.get("龙虎榜净买额", 0.0)),
                        buy_amount=float(row.get("龙虎榜买入额", 0.0)),
                        sell_amount=float(row.get("龙虎榜卖出额", 0.0)),
                        buy_seats=buy_seats,
                        sell_seats=sell_seats,
                    )
                )

            logger.info(f"成功获取 {len(result)} 条龙虎榜记录：{date_str}")
            return result

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败：{date_str}，错误：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message=f"获取龙虎榜数据失败：{date_str}",
                details=f"stock_lhb_detail_em API 调用失败: {str(e)}",
            )

    async def fetch_sector_capital_flow(
        self, sector_type: str = "概念资金流"
    ) -> list[SectorCapitalFlowDTO]:
        """
        获取当日板块资金流向排名
        调用 akshare.stock_sector_fund_flow_rank(indicator="今日", sector_type=<type>) 接口
        
        Args:
            sector_type: 板块类型（默认"概念资金流"）
            
        Returns:
            list[SectorCapitalFlowDTO]: 板块资金流向数据列表
            
        Raises:
            AppException: API 调用失败时抛出
        """
        try:
            import akshare as ak

            logger.info(f"开始获取板块资金流向数据：{sector_type}")
            df: pd.DataFrame = await self._rate_limited_call(
                ak.stock_sector_fund_flow_rank, indicator="今日", sector_type=sector_type
            )

            if df is None or df.empty:
                logger.warning(f"板块资金流向数据为空：{sector_type}")
                return []

            result: list[SectorCapitalFlowDTO] = []
            for _, row in df.iterrows():
                result.append(
                    SectorCapitalFlowDTO(
                        sector_name=str(row.get("名称", "")),
                        sector_type=sector_type,
                        net_amount=float(row.get("今日主力净流入-净额", 0.0)),
                        inflow_amount=float(row.get("今日主力净流入-流入额", 0.0)),
                        outflow_amount=float(row.get("今日主力净流入-流出额", 0.0)),
                        pct_chg=float(row.get("今日涨跌幅", 0.0)),
                    )
                )

            logger.info(f"成功获取 {len(result)} 条板块资金流向记录：{sector_type}")
            return result

        except ImportError as e:
            logger.error("akshare 库未安装或导入失败")
            raise AppException(
                status_code=500,
                code="AKSHARE_IMPORT_ERROR",
                message="akshare 数据服务不可用",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"获取板块资金流向数据失败：{sector_type}，错误：{str(e)}")
            raise AppException(
                status_code=500,
                code="AKSHARE_API_ERROR",
                message=f"获取板块资金流向数据失败：{sector_type}",
                details=f"stock_sector_fund_flow_rank API 调用失败: {str(e)}",
            )
