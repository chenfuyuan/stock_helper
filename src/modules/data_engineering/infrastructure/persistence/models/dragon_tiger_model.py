from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INTEGER, JSONB

from src.shared.infrastructure.db.base import Base


class DragonTigerModel(Base):
    """
    龙虎榜数据库模型
    映射 de_dragon_tiger 表
    """

    __tablename__ = "de_dragon_tiger"

    id = Column(INTEGER, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    third_code = Column(String(20), nullable=False, index=True, comment="股票代码（系统标准格式）")
    stock_name = Column(String(100), nullable=False, comment="股票名称")
    pct_chg = Column(Float, nullable=False, comment="涨跌幅（百分比）")
    close = Column(Float, nullable=False, comment="收盘价")
    reason = Column(String(200), nullable=False, comment="上榜原因")
    net_amount = Column(Float, nullable=False, comment="龙虎榜净买入额")
    buy_amount = Column(Float, nullable=False, comment="买入总额")
    sell_amount = Column(Float, nullable=False, comment="卖出总额")
    buy_seats = Column(JSONB, nullable=False, default=list, comment="买入席位详情（JSONB）")
    sell_seats = Column(JSONB, nullable=False, default=list, comment="卖出席位详情（JSONB）")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    __table_args__ = (
        UniqueConstraint("trade_date", "third_code", "reason", name="uq_dragon_tiger"),
    )
