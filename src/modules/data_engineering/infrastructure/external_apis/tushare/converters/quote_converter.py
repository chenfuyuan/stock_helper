import pandas as pd
from typing import List, Optional
from loguru import logger
from src.modules.data_engineering.domain.model.stock_daily import StockDaily

class StockDailyAssembler:
    """
    股票日线数据装配器
    """
    
    @staticmethod
    def to_domain_list(df: pd.DataFrame) -> List[StockDaily]:
        """
        将 Tushare DataFrame 转换为 StockDaily 领域对象列表
        """
        dailies = []
        if df is None or df.empty:
            return dailies
            
        # 处理空值：将 NaN 替换为 None
        df = df.where(pd.notnull(df), None)
        
        for _, row in df.iterrows():
            try:
                daily = StockDailyAssembler._row_to_entity(row)
                if daily:
                    dailies.append(daily)
            except Exception as e:
                logger.warning(f"日线数据转换失败: {row.get('ts_code', 'unknown')} - {str(e)}")
                continue
                
        return dailies

    @staticmethod
    def _row_to_entity(row: pd.Series) -> Optional[StockDaily]:
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return pd.to_datetime(date_str).date()
            except ValueError:
                return None

        return StockDaily(
            third_code=row['ts_code'],
            trade_date=parse_date(row['trade_date']),
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            pre_close=row['pre_close'],
            change=row['change'],
            pct_chg=row['pct_chg'],
            vol=row['vol'],
            amount=row['amount'],
            
            # 新增字段 (使用 get 避免 KeyErrors，如果 column 不存在则返回 None)
            adj_factor=row.get('adj_factor'),
            turnover_rate=row.get('turnover_rate'),
            turnover_rate_f=row.get('turnover_rate_f'),
            volume_ratio=row.get('volume_ratio'),
            pe=row.get('pe'),
            pe_ttm=row.get('pe_ttm'),
            pb=row.get('pb'),
            ps=row.get('ps'),
            ps_ttm=row.get('ps_ttm'),
            dv_ratio=row.get('dv_ratio'),
            dv_ttm=row.get('dv_ttm'),
            total_share=row.get('total_share'),
            float_share=row.get('float_share'),
            free_share=row.get('free_share'),
            total_mv=row.get('total_mv'),
            circ_mv=row.get('circ_mv'),
            
            source="tushare"
        )
