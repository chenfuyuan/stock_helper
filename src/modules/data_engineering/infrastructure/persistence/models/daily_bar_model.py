from sqlalchemy import Column, Date, Float, String

from src.shared.infrastructure.db.base import Base


class StockDailyModel(Base):
    """
    股票日线行情数据库模型
    Stock Daily Quotation Database Model
    """

    __tablename__ = "stock_daily"

    third_code = Column(
        String(20),
        primary_key=True,
        nullable=False,
        index=True,
        comment="第三方代码",
    )
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

    # 复权因子
    adj_factor = Column(Float, nullable=True, comment="复权因子")

    # 每日指标
    turnover_rate = Column(Float, nullable=True, comment="换手率")
    turnover_rate_f = Column(Float, nullable=True, comment="换手率(自由流通股)")
    volume_ratio = Column(Float, nullable=True, comment="量比")
    pe = Column(Float, nullable=True, comment="市盈率")
    pe_ttm = Column(Float, nullable=True, comment="市盈率TTM")
    pb = Column(Float, nullable=True, comment="市净率")
    ps = Column(Float, nullable=True, comment="市销率")
    ps_ttm = Column(Float, nullable=True, comment="市销率TTM")
    dv_ratio = Column(Float, nullable=True, comment="股息率")
    dv_ttm = Column(Float, nullable=True, comment="股息率TTM")
    total_share = Column(Float, nullable=True, comment="总股本")
    float_share = Column(Float, nullable=True, comment="流通股本")
    free_share = Column(Float, nullable=True, comment="自由流通股本")
    total_mv = Column(Float, nullable=True, comment="总市值")
    circ_mv = Column(Float, nullable=True, comment="流通市值")

    source = Column(String(20), nullable=True, default="tushare", comment="数据来源")
