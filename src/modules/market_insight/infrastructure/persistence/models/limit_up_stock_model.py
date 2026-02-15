"""
涨停股票 ORM 模型
"""

from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.db.base import Base


class LimitUpStockModel(Base):
    """涨停股票数据库模型"""

    __tablename__ = "mi_limit_up_stock"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    third_code = Column(String(20), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(100), nullable=False, comment="股票名称")
    pct_chg = Column(Float, nullable=False, comment="涨跌幅（百分比）")
    close = Column(Float, nullable=False, comment="收盘价")
    amount = Column(Float, nullable=False, comment="成交额")
    concepts = Column(JSONB, nullable=False, server_default="[]", comment="所属概念板块对象列表")
    limit_type = Column(String(20), nullable=False, comment="涨停类型")

    __table_args__ = (
        UniqueConstraint("trade_date", "third_code", name="uq_mi_limit_up_date_code"),
    )
