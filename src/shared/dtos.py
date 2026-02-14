from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class BaseResponse(BaseModel, Generic[DataT]):
    """
    标准 API 响应结构

    Attributes:
        success (bool): 业务处理是否成功
        message (str): 响应消息描述
        data (DataT | None): 业务返回数据
        code (str): 响应代码，用于前端逻辑判断
    """

    success: bool = True
    message: str = "Success"
    data: DataT | None = None
    code: str | None = None


class ErrorResponse(BaseModel):
    """
    标准错误响应结构

    Attributes:
        success (bool): 固定为 False
        message (str): 友好的错误提示
        code (str): 内部错误码，用于前端逻辑判断
    """

    success: bool = False
    message: str
    code: str
