"""
占位符值类型：标量可传 float/int/str，序列传 list，N/A 用 "N/A" 字符串。
与 User Prompt 模板占位符一一对应，统一此处定义避免各 DTO 文件重复。
"""
from typing import Union

PlaceholderValue = Union[float, int, str, list[float], list[int], list[str]]
