from sqlalchemy import Column, Date, Integer, String

from src.shared.infrastructure.db.base import Base


class StockModel(Base):
    """
    股票信息数据库模型
    Stock Information Database Model
    """

    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, index=True)
    third_code = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="第三方代码",
    )
    symbol = Column(
        String(10), unique=True, nullable=False, index=True, comment="股票代码"
    )
    name = Column(String(100), nullable=False, comment="股票名称")
    area = Column(String(50), nullable=True, comment="所在地域")
    industry = Column(
        String(50), nullable=True, index=True, comment="所属行业"
    )
    market = Column(String(20), nullable=True, index=True, comment="市场类型")
    list_date = Column(Date, nullable=True, comment="上市日期")

    # 新增字段
    fullname = Column(String(200), nullable=True, comment="股票全称")
    enname = Column(String(200), nullable=True, comment="英文全称")
    cnspell = Column(String(50), nullable=True, comment="拼音缩写")
    exchange = Column(String(20), nullable=True, comment="交易所代码")
    curr_type = Column(String(20), nullable=True, comment="交易货币")
    list_status = Column(
        String(10), nullable=True, comment="上市状态 L上市 D退市 P暂停上市"
    )
    delist_date = Column(Date, nullable=True, comment="退市日期")
    is_hs = Column(
        String(10),
        nullable=True,
        comment="是否沪深港通标的，N否 H沪股通 S深股通",
    )

    # 来源标记
    source = Column(
        String(20), nullable=True, default="tushare", comment="数据来源"
    )

    # 财务数据同步状态
    last_finance_sync_date = Column(
        Date, nullable=True, comment="上次财务数据同步时间"
    )
