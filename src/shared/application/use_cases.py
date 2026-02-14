from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputDTO = TypeVar("InputDTO")
OutputDTO = TypeVar("OutputDTO")


class BaseUseCase(ABC, Generic[InputDTO, OutputDTO]):
    """
    应用层用例 (Use Case) 基类
    定义了业务逻辑执行的标准接口
    """

    @abstractmethod
    async def execute(self, input_dto: InputDTO) -> OutputDTO:
        """
        执行用例
        :param input_dto: 输入数据传输对象
        :return: 输出数据传输对象
        """
