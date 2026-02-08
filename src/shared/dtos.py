from typing import Generic, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")


class BaseResponse(BaseModel, Generic[DataT]):
    """
    标准 API 响应结构
    """
    success: bool = True
    message: str = "Success"
    data: DataT | None = None


class ErrorResponse(BaseModel):
    """
    标准错误响应结构
    """
    success: bool = False
    message: str
    code: str
