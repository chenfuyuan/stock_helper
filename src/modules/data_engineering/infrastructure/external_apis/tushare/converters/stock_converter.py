import pandas as pd
from typing import List, Optional
from loguru import logger
from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.data_engineering.domain.model.enums import ListStatus, IsHs, ExchangeType, MarketType

class StockAssembler:
    """
    股票数据装配器
    负责将外部数据(DTO/DataFrame)转换为领域实体(Entity)
    """
    
    @staticmethod
    def to_domain_list(df: pd.DataFrame) -> List[StockInfo]:
        """
        将 Tushare DataFrame 转换为 StockInfo 领域对象列表
        """
        stocks = []
        if df is None or df.empty:
            return stocks
            
        # 处理空值：将 NaN 替换为 None
        df = df.where(pd.notnull(df), None)
        
        for _, row in df.iterrows():
            try:
                stock = StockAssembler._row_to_entity(row)
                if stock:
                    stocks.append(stock)
            except Exception as e:
                # 单条数据转换失败不应中断整个流程，记录日志即可
                logger.warning(f"股票数据转换失败: {row.get('ts_code', 'unknown')} - {str(e)}")
                continue
                
        logger.info(f"成功转换 {len(stocks)} 条股票数据")
        return stocks

    @staticmethod
    def _row_to_entity(row: pd.Series) -> Optional[StockInfo]:
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return pd.to_datetime(date_str).date()
            except ValueError:
                logger.warning(f"日期格式转换失败: {date_str}")
                return None

        # 安全的枚举转换
        def safe_enum(enum_cls, value):
            try:
                return enum_cls(value) if value else None
            except ValueError:
                return None

        return StockInfo(
            third_code=row['ts_code'], # 映射 ts_code -> third_code
            symbol=row['symbol'],
            name=row['name'],
            area=row['area'],
            industry=row['industry'],
            market=safe_enum(MarketType, row['market']),
            list_date=parse_date(row['list_date']),
            fullname=row['fullname'],
            enname=row['enname'],
            cnspell=row['cnspell'],
            exchange=safe_enum(ExchangeType, row['exchange']),
            curr_type=row['curr_type'],
            list_status=safe_enum(ListStatus, row['list_status']),
            delist_date=parse_date(row['delist_date']),
            is_hs=safe_enum(IsHs, row['is_hs']),
            source="tushare"
        )
