from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from src.shared.infrastructure.db.base import Base


class ConceptModel(Base):
    """
    概念板块数据库模型
    映射 concept 表
    """

    __tablename__ = "concept"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True, comment="概念板块代码")
    name = Column(String(100), nullable=False, comment="概念板块名称")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


class ConceptStockModel(Base):
    """
    概念-股票映射数据库模型
    映射 concept_stock 表
    """

    __tablename__ = "concept_stock"

    id = Column(Integer, primary_key=True, index=True)
    concept_code = Column(String(20), nullable=False, index=True, comment="概念板块代码")
    third_code = Column(String(20), nullable=False, index=True, comment="股票代码（系统标准格式）")
    stock_name = Column(String(100), nullable=True, comment="股票名称")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    __table_args__ = (
        UniqueConstraint("concept_code", "third_code", name="uq_concept_stock"),
    )
