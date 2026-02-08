from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    SQLAlchemy 声明式基类
    所有 ORM 模型应继承此类
    """
    id: Any
    __name__: str

    # 自动生成 __tablename__
    # 默认将类名转换为小写作为表名
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
