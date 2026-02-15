from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, UniqueConstraint

from src.shared.infrastructure.db.base import Base


class PreviousLimitUpModel(Base):
    """
    昨日涨停表现数据库模型
    映射 de_previous_limit_up 表
    """

    __tablename__ = "de_previous_limit_up"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期（今日日期，即表现观察日）")
    third_code = Column(String(20), nullable=False, index=True, comment="股票代码（系统标准格式）")
    stock_name = Column(String(100), nullable=False, comment="股票名称")
    pct_chg = Column(Float, nullable=False, comment="今日涨跌幅（百分比）")
    close = Column(Float, nullable=False, comment="最新价")
    amount = Column(Float, nullable=False, comment="成交额")
    turnover_rate = Column(Float, nullable=False, comment="换手率")
    yesterday_consecutive_boards = Column(Integer, nullable=False, comment="昨日连板天数")
    industry = Column(String(100), nullable=False, comment="所属行业")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    __table_args__ = (UniqueConstraint("trade_date", "third_code", name="uq_previous_limit_up"),)
