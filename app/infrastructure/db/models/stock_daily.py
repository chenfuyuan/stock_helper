from sqlalchemy import Column, String, Date, Float
from app.infrastructure.db.base import Base

class StockDailyModel(Base):
    """
    股票日线行情数据库模型
    Stock Daily Quotation Database Model
    """
    __tablename__ = "stock_daily"

    third_code = Column(String(20), primary_key=True, nullable=False, index=True, comment="第三方代码")
    trade_date = Column(Date, primary_key=True, nullable=False, index=True, comment="交易日期")
    open = Column(Float, nullable=True, comment="开盘价")
    high = Column(Float, nullable=True, comment="最高价")
    low = Column(Float, nullable=True, comment="最低价")
    close = Column(Float, nullable=True, comment="收盘价")
    pre_close = Column(Float, nullable=True, comment="昨收价")
    change = Column(Float, nullable=True, comment="涨跌额")
    pct_chg = Column(Float, nullable=True, comment="涨跌幅")
    vol = Column(Float, nullable=True, comment="成交量")
    amount = Column(Float, nullable=True, comment="成交额")
    source = Column(String(20), nullable=True, default="tushare", comment="数据来源")
