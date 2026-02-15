from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, UniqueConstraint

from src.shared.infrastructure.db.base import Base


class SectorCapitalFlowModel(Base):
    """
    板块资金流向数据库模型
    映射 de_sector_capital_flow 表
    """

    __tablename__ = "de_sector_capital_flow"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    sector_name = Column(String(100), nullable=False, index=True, comment="板块名称")
    sector_type = Column(String(50), nullable=False, index=True, comment="板块类型（如'概念资金流'）")
    net_amount = Column(Float, nullable=False, comment="净流入额（万元）")
    inflow_amount = Column(Float, nullable=False, comment="流入额（万元）")
    outflow_amount = Column(Float, nullable=False, comment="流出额（万元）")
    pct_chg = Column(Float, nullable=False, comment="板块涨跌幅（百分比）")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "sector_name", "sector_type", name="uq_sector_capital_flow"
        ),
    )
