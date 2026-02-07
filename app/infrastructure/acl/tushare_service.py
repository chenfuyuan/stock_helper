import pandas as pd
import tushare as ts
from typing import List, Optional
from loguru import logger
from app.core.config import settings
from app.domain.stock.entity import StockInfo
from app.core.exceptions import AppException

class TushareService:
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
                
            return self._transform_to_domain(df)
            
        except Exception as e:
            logger.error(f"获取股票数据失败: {str(e)}")
            raise AppException(
                status_code=502, # Bad Gateway
                code="TUSHARE_FETCH_ERROR", 
                message="获取第三方股票数据失败",
                details=str(e)
            )

    def _transform_to_domain(self, df: pd.DataFrame) -> List[StockInfo]:
        """
        将 Pandas DataFrame 转换为 StockInfo 领域对象列表 (数据清洗与映射)
        """
        stocks = []
        # 处理空值：将 NaN 替换为 None
        df = df.where(pd.notnull(df), None)
        
        for _, row in df.iterrows():
            try:
                # 转换上市日期格式 YYYYMMDD -> YYYY-MM-DD
                def parse_date(date_str):
                    if not date_str:
                        return None
                    try:
                        return pd.to_datetime(date_str).date()
                    except ValueError:
                        logger.warning(f"日期格式转换失败: {date_str}")
                        return None

                stock = StockInfo(
                    third_code=row['ts_code'], # 映射 ts_code -> third_code
                    symbol=row['symbol'],
                    name=row['name'],
                    area=row['area'],
                    industry=row['industry'],
                    market=row['market'],
                    list_date=parse_date(row['list_date']),
                    fullname=row['fullname'],
                    enname=row['enname'],
                    cnspell=row['cnspell'],
                    exchange=row['exchange'],
                    curr_type=row['curr_type'],
                    list_status=row['list_status'],
                    delist_date=parse_date(row['delist_date']),
                    is_hs=row['is_hs'],
                    source="tushare"
                )
                stocks.append(stock)
            except Exception as e:
                # 单条数据转换失败不应中断整个流程，记录日志即可
                logger.warning(f"股票数据转换失败: {row.get('ts_code', 'unknown')} - {str(e)}")
                continue
                
        logger.info(f"成功转换 {len(stocks)} 条股票数据")
        return stocks
