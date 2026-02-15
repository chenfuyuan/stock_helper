"""
概念热度 ORM 模型
"""

from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint

from src.shared.infrastructure.db.base import Base


class ConceptHeatModel(Base):
    """概念热度数据库模型"""

    __tablename__ = "mi_concept_heat"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    concept_code = Column(String(50), nullable=False, index=True, comment="概念板块代码")
    concept_name = Column(String(100), nullable=False, comment="概念板块名称")
    avg_pct_chg = Column(Float, nullable=False, comment="等权平均涨跌幅（百分比）")
    stock_count = Column(Integer, nullable=False, comment="成分股总数")
    up_count = Column(Integer, nullable=False, comment="上涨家数")
    down_count = Column(Integer, nullable=False, comment="下跌家数")
    limit_up_count = Column(Integer, nullable=False, comment="涨停家数")
    total_amount = Column(Float, nullable=False, comment="板块成交额合计")

    __table_args__ = (
        UniqueConstraint("trade_date", "concept_code", name="uq_mi_concept_heat_date_code"),
    )
