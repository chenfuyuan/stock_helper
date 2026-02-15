import asyncio
import time
from typing import List, Optional

import pandas as pd
import tushare as ts
from loguru import logger

from src.modules.data_engineering.domain.model.disclosure import (
    StockDisclosure,
)
from src.modules.data_engineering.domain.model.financial_report import (
    StockFinance,
)
from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.data_engineering.domain.model.stock_daily import StockDaily
from src.modules.data_engineering.domain.ports.providers.financial_data_provider import (
    IFinancialDataProvider,
)
from src.modules.data_engineering.domain.ports.providers.market_quote_provider import (
    IMarketQuoteProvider,
)
from src.modules.data_engineering.domain.ports.providers.stock_basic_provider import (
    IStockBasicProvider,
)
from src.modules.data_engineering.infrastructure.config import de_config
from src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter import (
    SlidingWindowRateLimiter,
)
from src.modules.data_engineering.infrastructure.external_apis.tushare.converters.finance_converter import (  # noqa: E501
    StockFinanceAssembler,
)
from src.modules.data_engineering.infrastructure.external_apis.tushare.converters.quote_converter import (  # noqa: E501
    StockDailyAssembler,
)
from src.modules.data_engineering.infrastructure.external_apis.tushare.converters.stock_converter import (  # noqa: E501
    StockAssembler,
)
from src.modules.data_engineering.infrastructure.external_apis.tushare.converters.stock_disclosure_assembler import (  # noqa: E501
    StockDisclosureAssembler,
)
from src.shared.domain.exceptions import AppException

# Tushare 滑动窗口限速器：全进程共享
_tushare_rate_limiter: SlidingWindowRateLimiter | None = None


def _get_tushare_rate_limiter() -> SlidingWindowRateLimiter:
    """获取进程内共享的 Tushare 滑动窗口限速器。"""
    global _tushare_rate_limiter
    if _tushare_rate_limiter is None:
        _tushare_rate_limiter = SlidingWindowRateLimiter(
            max_calls=de_config.TUSHARE_RATE_LIMIT_MAX_CALLS,
            window_seconds=de_config.TUSHARE_RATE_LIMIT_WINDOW_SECONDS,
        )
    return _tushare_rate_limiter


class TushareClient(IStockBasicProvider, IMarketQuoteProvider, IFinancialDataProvider):
    """
    Tushare Client Adapter (Infrastructure Layer)
    Implements all data provider interfaces.
    """

    def __init__(self):
        # 初始化 Tushare Pro 接口
        if not de_config.TUSHARE_TOKEN or de_config.TUSHARE_TOKEN == "your_tushare_token_here":
            logger.warning("Tushare Token 未配置，可能无法获取数据")

        try:
            ts.set_token(de_config.TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        except Exception as e:
            logger.error(f"Tushare 初始化失败: {str(e)}")
            raise AppException(
                status_code=500,
                code="TUSHARE_INIT_ERROR",
                message="第三方数据服务初始化失败",
                details=str(e),
            )

    async def _run_in_executor(self, func, *args, **kwargs):
        """
        在默认线程池中执行同步函数，避免阻塞事件循环
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _rate_limited_call(self, func, *args, **kwargs):
        """
        带限速的 Tushare API 调用，使用滑动窗口限速器。
        支持频率超限异常的指数退避重试（最多 3 次）。
        """
        limiter = _get_tushare_rate_limiter()
        max_retries = 3
        base_wait = 3.0  # 基础等待时间（秒）
        
        for retry in range(max_retries + 1):
            try:
                # 获取调用许可（滑动窗口限速）
                await limiter.acquire()
                
                # 执行实际调用
                result = await self._run_in_executor(func, *args, **kwargs)
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 检查是否为频率超限异常（关键词匹配）
                is_rate_limit_error = (
                    "频率" in error_msg or
                    "每分钟" in error_msg or
                    "rate limit" in error_msg or
                    "too many requests" in error_msg
                )
                
                if is_rate_limit_error and retry < max_retries:
                    # 指数退避重试
                    wait_time = base_wait * (2 ** retry)
                    logger.warning(
                        f"TuShare 频率超限，第 {retry + 1} 次重试，等待 {wait_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # 非频率超限异常或已达最大重试次数，直接抛出
                    if is_rate_limit_error:
                        logger.error(f"TuShare 频率超限，已达最大重试次数 ({max_retries})")
                    raise

    async def fetch_disclosure_date(
        self, actual_date: Optional[str] = None
    ) -> List[StockDisclosure]:
        """
        获取财报披露计划
        """
        try:
            logger.info(f"开始从 Tushare 获取财报披露计划: actual_date={actual_date}")
            fields = "ts_code,ann_date,end_date,pre_date,actual_date"

            df = await self._rate_limited_call(
                self.pro.disclosure_date,
                actual_date=actual_date,
                fields=fields,
            )

            if df is None or df.empty:
                logger.warning(f"Tushare 财报披露计划为空: actual_date={actual_date}")
                return []

            return StockDisclosureAssembler.to_domain_list(df)

        except Exception as e:
            logger.error(f"获取财报披露计划失败: {str(e)}")
            raise AppException(
                status_code=502,
                code="TUSHARE_FETCH_ERROR",
                message="获取财报披露计划失败",
                details=str(e),
            )

    async def fetch_fina_indicator(
        self,
        third_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[StockFinance]:
        """
        获取财务指标数据
        """
        try:
            logger.info(
                f"开始从 Tushare 获取财务指标: code={third_code}, start={start_date}, end={end_date}"
            )
            fields = (
                "ts_code,ann_date,end_date,eps,dt_eps,total_revenue_ps,revenue_ps,capital_rese_ps,"  # noqa: E501
                "surplus_rese_ps,undist_profit_ps,extra_item,profit_dedt,gross_margin,current_ratio,"  # noqa: E501
                "quick_ratio,cash_ratio,inv_turn,ar_turn,ca_turn,fa_turn,assets_turn,invturn_days,"  # noqa: E501
                "arturn_days,op_income,valuechange_income,interst_income,daa,ebit,ebitda,fcff,fcfe,"  # noqa: E501
                "current_exint,noncurrent_exint,interestdebt,netdebt,tangible_asset,working_capital,"  # noqa: E501
                "networking_capital,invest_capital,retained_earnings,diluted2_eps,bps,ocfps,retainedps,"  # noqa: E501
                "cfps,ebit_ps,fcff_ps,fcfe_ps,netprofit_margin,grossprofit_margin,cogs_of_sales,"  # noqa: E501
                "expense_of_sales,profit_to_gr,saleexp_to_gr,adminexp_of_gr,finaexp_of_gr,impai_ttm,"  # noqa: E501
                "gc_of_gr,op_of_gr,ebit_of_gr,roe,roe_waa,roe_dt,roa,npta,roic,roe_yearly,roa2_yearly,"  # noqa: E501
                "roe_avg,opincome_of_ebt,investincome_of_ebt,n_op_profit_of_ebt,tax_to_ebt,dtprofit_to_profit,"  # noqa: E501
                "salescash_to_or,ocf_to_or,ocf_to_opincome,capitalized_to_da,debt_to_assets,assets_to_eqt,"  # noqa: E501
                "dp_assets_to_eqt,ca_to_assets,nca_to_assets,tbassets_to_totalassets,int_to_talcap,"  # noqa: E501
                "eqt_to_talcapital,currentdebt_to_debt,longdeb_to_debt,ocf_to_shortdebt,debt_to_eqt"
            )

            df = await self._rate_limited_call(
                self.pro.fina_indicator,
                ts_code=third_code,
                start_date=start_date,
                end_date=end_date,
                fields=fields,
            )

            if df is None or df.empty:
                logger.warning(f"Tushare 财务指标数据为空: code={third_code}")
                return []

            return StockFinanceAssembler.to_domain_list(df)

        except Exception as e:
            logger.error(f"获取财务指标失败: {str(e)}")
            # 抛出异常，让上层调用者处理（如记录失败、重试等）
            raise AppException(
                status_code=502,
                code="TUSHARE_FETCH_ERROR",
                message="获取第三方财务指标数据失败",
                details=str(e),
            )

    async def fetch_stock_basic(self) -> List[StockInfo]:
        """
        获取股票列表并转换为领域对象
        """
        try:
            logger.info("开始从 Tushare 获取股票基础数据...")
            # 获取数据字段：ts_code, symbol, name, area, industry, market, list_date, fullname, enname, cnspell,  # noqa: E501
# exchange, curr_type, list_status, delist_date, is_hs
            fields = (
                "ts_code,symbol,name,area,industry,market,list_date,fullname,enname,cnspell,"  # noqa: E501
                "exchange,curr_type,list_status,delist_date,is_hs"
            )

            df = await self._rate_limited_call(
                self.pro.stock_basic,
                exchange="",
                list_status="L",
                fields=fields,
            )

            if df is None or df.empty:
                logger.warning("Tushare 返回数据为空")
                return []

            return StockAssembler.to_domain_list(df)

        except Exception as e:
            logger.error(f"获取股票数据失败: {str(e)}")
            raise AppException(
                status_code=502,  # Bad Gateway
                code="TUSHARE_FETCH_ERROR",
                message="获取第三方股票数据失败",
                details=str(e),
            )

    async def fetch_daily(
        self,
        third_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[StockDaily]:
        """
        获取日线行情数据（包含复权因子和每日指标）
        """
        try:
            logger.info(
                f"开始从 Tushare 获取日线数据: code={third_code}, date={trade_date}, "  # noqa: E501
                f"start={start_date}, end={end_date}"
            )
            # 1. 获取基础行情 (daily)
            # fields: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount  # noqa: E501
            daily_fields = (
                "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"
            )
            df_daily = await self._rate_limited_call(
                self.pro.daily,
                ts_code=third_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                fields=daily_fields,
            )

            if df_daily is None or df_daily.empty:
                logger.warning(f"Tushare 日线数据为空: code={third_code}, date={trade_date}")
                return []

            # 2. 获取复权因子 (adj_factor)
            # fields: ts_code, trade_date, adj_factor
            adj_fields = "ts_code,trade_date,adj_factor"
            try:
                df_adj = await self._rate_limited_call(
                    self.pro.adj_factor,
                    ts_code=third_code,
                    trade_date=trade_date,
                    start_date=start_date,
                    end_date=end_date,
                    fields=adj_fields,
                )
            except Exception as e:
                logger.warning(f"获取复权因子失败: {str(e)}")
                df_adj = pd.DataFrame()

            # 3. 获取每日指标 (daily_basic)
            # fields: ts_code, trade_date, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm,  # noqa: E501
# dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv
            basic_fields = (
                "ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,"  # noqa: E501
                "dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv"
            )
            try:
                df_basic = await self._rate_limited_call(
                    self.pro.daily_basic,
                    ts_code=third_code,
                    trade_date=trade_date,
                    start_date=start_date,
                    end_date=end_date,
                    fields=basic_fields,
                )
            except Exception as e:
                logger.warning(f"获取每日指标失败: {str(e)}")
                df_basic = pd.DataFrame()

            # 4. 数据合并 (ETL)
            # 预处理：去重，防止因数据源重复导致 merge 后数据膨胀
            if df_daily is not None and not df_daily.empty:
                df_daily = df_daily.drop_duplicates(subset=["ts_code", "trade_date"])

            result_df = df_daily

            if df_adj is not None and not df_adj.empty:
                df_adj = df_adj.drop_duplicates(subset=["ts_code", "trade_date"])
                result_df = pd.merge(result_df, df_adj, on=["ts_code", "trade_date"], how="left")

            if df_basic is not None and not df_basic.empty:
                df_basic = df_basic.drop_duplicates(subset=["ts_code", "trade_date"])
                result_df = pd.merge(
                    result_df,
                    df_basic,
                    on=["ts_code", "trade_date"],
                    how="left",
                )

            return StockDailyAssembler.to_domain_list(result_df)

        except Exception as e:
            logger.error(f"获取日线数据失败: {str(e)}")
            raise AppException(
                status_code=502,
                code="TUSHARE_FETCH_ERROR",
                message="获取第三方日线数据失败",
                details=str(e),
            )
