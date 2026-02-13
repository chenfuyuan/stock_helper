# 目标资产
- 标的代码: {symbol}

# 辩论结论（输入）

以下是多空辩论的结论，请基于此输出最终裁决（操作方向、仓位、入场/止损/止盈、风控约束）。

- **综合方向**: {direction}
- **综合置信度**: {confidence}

## 多头核心论点
{bull_thesis}

## 空头核心论点
{bear_thesis}

## 风险因子摘要
{risk_factors}

## 核心分歧点
{key_disagreements}

## 冲突消解结论
{conflict_resolution}

---

# 你的任务
基于以上辩论结论，输出 **可执行的投资操作指令**（action、position_percent、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning）。
请严格按照 system prompt 中定义的 JSON 格式输出结果，且 action 仅能为 BUY、SELL 或 HOLD。
