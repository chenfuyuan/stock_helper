import pandas as pd
import tushare as ts
from typing import List, Optional
from loguru import logger
from app.core.config import settings
from app.domain.stock.entities import StockInfo, StockDaily, StockFinance
from app.domain.stock.service import StockDataProvider
from app.core.exceptions import AppException
from app.infrastructure.acl.assembler import StockAssembler, StockDailyAssembler, StockFinanceAssembler

class TushareService(StockDataProvider):
    """
    Tushare 服务适配器 (防腐层)
    负责调用 Tushare 接口并将数据转换为领域对象
    """
    def __init__(self):
        # 初始化 Tushare Pro 接口
        if not settings.TUSHARE_TOKEN or settings.TUSHARE_TOKEN == "your_tushare_token_here":
            logger.warning("Tushare Token 未配置，可能无法获取数据")
        
        try:
            ts.set_token(settings.TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        except Exception as e:
            logger.error(f"Tushare 初始化失败: {str(e)}")
            raise AppException(
                status_code=500,
                code="TUSHARE_INIT_ERROR",
                message="第三方数据服务初始化失败",
                details=str(e)
            )

    async def fetch_fina_indicator(self, third_code: str = None, start_date: str = None, end_date: str = None) -> List[StockFinance]:
        """
        获取财务指标数据
        """
        try:
            fields = 'ts_code,ann_date,end_date,eps,dt_eps,total_revenue_ps,revenue_ps,capital_rese_ps,surplus_rese_ps,undist_profit_ps,extra_item,profit_dedt,gross_margin,current_ratio,quick_ratio,cash_ratio,inv_turn,ar_turn,ca_turn,fa_turn,assets_turn,invturn_days,arturn_days,op_income,valuechange_income,interst_income,daa,ebit,ebitda,fcff,fcfe,current_exint,noncurrent_exint,interestdebt,netdebt,tangible_asset,working_capital,networking_capital,invest_capital,retained_earnings,diluted2_eps,bps,ocfps,retainedps,cfps,ebit_ps,fcff_ps,fcfe_ps,netprofit_margin,grossprofit_margin,cogs_of_sales,expense_of_sales,profit_to_gr,saleexp_to_gr,adminexp_of_gr,finaexp_of_gr,impai_ttm,gc_of_gr,op_of_gr,ebit_of_gr,roe,roe_waa,roe_dt,roa,npta,roic,roe_yearly,roa2_yearly,roe_avg,opincome_of_ebt,investincome_of_ebt,n_op_profit_of_ebt,tax_to_ebt,dtprofit_to_profit,salescash_to_or,ocf_to_or,ocf_to_opincome,capitalized_to_da,debt_to_assets,assets_to_eqt,dp_assets_to_eqt,ca_to_assets,nca_to_assets,tbassets_to_totalassets,int_to_talcap,eqt_to_talcapital,currentdebt_to_debt,longdeb_to_debt,ocf_to_shortdebt,debt_to_eqt'
            
            df = self.pro.fina_indicator(ts_code=third_code, start_date=start_date, end_date=end_date, fields=fields)
            
            if df is None or df.empty:
                return []
                
            return StockFinanceAssembler.to_domain_list(df)
            
        except Exception as e:
            logger.error(f"获取财务指标失败: {str(e)}")
            # 抛出异常，让上层调用者处理（如记录失败、重试等）
            raise AppException(
                status_code=502,
                code="TUSHARE_FETCH_ERROR",
                message="获取第三方财务指标数据失败",
                details=str(e)
            )

    async def fetch_stock_basic(self) -> List[StockInfo]:
        """
        获取股票列表并转换为领域对象
        """
        try:
            logger.info("开始从 Tushare 获取股票基础数据...")
            # 获取数据字段：ts_code, symbol, name, area, industry, market, list_date, fullname, enname, cnspell, exchange, curr_type, list_status, delist_date, is_hs
            fields = 'ts_code,symbol,name,area,industry,market,list_date,fullname,enname,cnspell,exchange,curr_type,list_status,delist_date,is_hs'
            
            # 由于 tushare 是同步库，这里直接调用
            # 在高并发场景下应该放到线程池中运行，但对于这种后台同步任务，直接调用通常可以接受
            # 或者使用 run_in_executor
            df = self.pro.stock_basic(exchange='', list_status='L', fields=fields)
            
            if df is None or df.empty:
                logger.warning("Tushare 返回数据为空")
                return []
                
            return StockAssembler.to_domain_list(df)
            
        except Exception as e:
            logger.error(f"获取股票数据失败: {str(e)}")
            raise AppException(
                status_code=502, # Bad Gateway
                code="TUSHARE_FETCH_ERROR", 
                message="获取第三方股票数据失败",
                details=str(e)
            )

    async def fetch_daily(self, third_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None) -> List[StockDaily]:
        """
        获取日线行情数据（包含复权因子和每日指标）
        """
        try:
            # 1. 获取基础行情 (daily)
            # fields: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
            daily_fields = 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
            df_daily = self.pro.daily(ts_code=third_code, trade_date=trade_date, start_date=start_date, end_date=end_date, fields=daily_fields)
            
            if df_daily is None or df_daily.empty:
                return []
                
            # 2. 获取复权因子 (adj_factor)
            # fields: ts_code, trade_date, adj_factor
            adj_fields = 'ts_code,trade_date,adj_factor'
            try:
                df_adj = self.pro.adj_factor(ts_code=third_code, trade_date=trade_date, start_date=start_date, end_date=end_date, fields=adj_fields)
            except Exception as e:
                logger.warning(f"获取复权因子失败: {str(e)}")
                df_adj = pd.DataFrame()

            # 3. 获取每日指标 (daily_basic)
            # fields: ts_code, trade_date, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv
            basic_fields = 'ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            try:
                df_basic = self.pro.daily_basic(ts_code=third_code, trade_date=trade_date, start_date=start_date, end_date=end_date, fields=basic_fields)
            except Exception as e:
                logger.warning(f"获取每日指标失败: {str(e)}")
                df_basic = pd.DataFrame()
            
            # 4. 数据合并 (ETL)
            # 预处理：去重，防止因数据源重复导致 merge 后数据膨胀
            if df_daily is not None and not df_daily.empty:
                df_daily = df_daily.drop_duplicates(subset=['ts_code', 'trade_date'])

            result_df = df_daily
            
            if df_adj is not None and not df_adj.empty:
                df_adj = df_adj.drop_duplicates(subset=['ts_code', 'trade_date'])
                result_df = pd.merge(result_df, df_adj, on=['ts_code', 'trade_date'], how='left')
                
            if df_basic is not None and not df_basic.empty:
                df_basic = df_basic.drop_duplicates(subset=['ts_code', 'trade_date'])
                result_df = pd.merge(result_df, df_basic, on=['ts_code', 'trade_date'], how='left')
                
            return StockDailyAssembler.to_domain_list(result_df)
            
        except Exception as e:
            logger.error(f"获取日线数据失败: {str(e)}")
            raise AppException(
                status_code=502,
                code="TUSHARE_FETCH_ERROR",
                message="获取第三方日线数据失败",
                details=str(e)
            )
