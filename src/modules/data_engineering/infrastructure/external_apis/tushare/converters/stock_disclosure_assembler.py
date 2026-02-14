from typing import List, Optional

import pandas as pd
from loguru import logger

from src.modules.data_engineering.domain.model.disclosure import (
    StockDisclosure,
)


class StockDisclosureAssembler:
    """
    StockDisclosure Assembler
    Convert Tushare DataFrame/Dict to StockDisclosure Domain Entity
    """

    @staticmethod
    def to_domain_list(df: pd.DataFrame) -> List[StockDisclosure]:
        result = []
        if df is None or df.empty:
            return result

        df = df.where(pd.notnull(df), None)

        for _, row in df.iterrows():
            try:
                disclosure = StockDisclosureAssembler._row_to_entity(row)
                if disclosure:
                    result.append(disclosure)
            except Exception as e:
                logger.warning(
                    f"财报披露计划转换失败: {row.get('ts_code', 'unknown')} - {str(e)}"
                )
                continue

        return result

    @staticmethod
    def _row_to_entity(row: pd.Series) -> Optional[StockDisclosure]:
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return pd.to_datetime(date_str).date()
            except ValueError:
                return None

        third_code = row.get("ts_code")
        # Tushare may return None for dates
        ann_date = parse_date(row.get("ann_date"))
        end_date = parse_date(row.get("end_date"))
        pre_date = parse_date(row.get("pre_date"))
        actual_date = parse_date(row.get("actual_date"))

        if not third_code or not end_date:
            return None

        return StockDisclosure(
            third_code=third_code,
            ann_date=ann_date,
            end_date=end_date,
            pre_date=pre_date,
            actual_date=actual_date,
        )
