"""
LangGraph 状态 Reducer 函数。

merge_dicts：合并两个 dict，用于并行节点各自写入 results/errors 后自动聚合。
"""


def merge_dicts(left: dict, right: dict) -> dict:
    """
    合并两个 dict，右值覆盖左值同 key。

    用于 Annotated[dict, merge_dicts]，使并行专家节点写入的 {expert_name: result} 自动合并。
    """
    return {**left, **right}
