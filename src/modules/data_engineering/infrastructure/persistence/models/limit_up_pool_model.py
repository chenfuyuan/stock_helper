from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, UniqueConstraint

from src.shared.infrastructure.db.base import Base


class LimitUpPoolModel(Base):
    """
    涨停池数据库模型
    映射 de_limit_up_pool 表
    """

    __tablename__ = "de_limit_up_pool"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    third_code = Column(String(20), nullable=False, index=True, comment="股票代码（系统标准格式）")
    stock_name = Column(String(100), nullable=False, comment="股票名称")
    pct_chg = Column(Float, nullable=False, comment="涨跌幅（百分比）")
    close = Column(Float, nullable=False, comment="最新价")
    amount = Column(Float, nullable=False, comment="成交额")
    turnover_rate = Column(Float, nullable=False, comment="换手率")
    consecutive_boards = Column(Integer, nullable=False, comment="连板天数（首板为 1）")
    first_limit_up_time = Column(String(20), nullable=True, comment="首次封板时间")
    last_limit_up_time = Column(String(20), nullable=True, comment="最后封板时间")
    industry = Column(String(100), nullable=False, comment="所属行业")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    __table_args__ = (UniqueConstraint("trade_date", "third_code", name="uq_limit_up_pool"),)
