## ADDED Requirements

### Requirement: 技术分析最低 K 线数量门槛
`TechnicalAnalystService.run()` 在获取日线数据后、计算指标前，SHALL 校验 K 线数量是否满足最低门槛（MIN_BARS_REQUIRED = 30）。不满足时 SHALL 抛出 `BadRequestException` 并给出明确的错误信息，告知用户所需的最低数据量。

#### Scenario: K 线数量充足（≥30 根）
- **WHEN** `TechnicalAnalystService.run()` 获取到 ≥ 30 根 K 线
- **THEN** 正常计算技术指标并调用 Agent，行为与当前一致

#### Scenario: K 线数量不足（<30 根且 >0 根）
- **WHEN** `TechnicalAnalystService.run()` 获取到 1-29 根 K 线
- **THEN** SHALL 抛出 `BadRequestException`，message 中包含实际获取到的 K 线数量和所需的最低数量（30），提示用户同步更多历史数据

#### Scenario: K 线为空（0 根）
- **WHEN** `TechnicalAnalystService.run()` 获取到 0 根 K 线
- **THEN** SHALL 抛出 `BadRequestException`，行为与当前一致（现有的 `if not bars` 检查）

---

### Requirement: 数据不足时指标使用 None 而非误导性默认值
`compute_technical_indicators()` 中，当数据量不足以计算某个指标时，该指标 SHALL 返回 `None`（而非 0.0 或 50.0 等合法但误导性的默认值）。对应的 `TechnicalIndicatorsSnapshot` DTO 中相关字段类型 SHALL 改为 `Optional[float]`。

#### Scenario: RSI 数据不足
- **WHEN** 计算 RSI(14) 但收盘价序列不足 15 根
- **THEN** `rsi_value` SHALL 为 `None`（而非当前的 50.0）

#### Scenario: MACD 数据不足
- **WHEN** 计算 MACD(12,26,9) 但收盘价序列不足 26 根
- **THEN** `macd_dif`、`macd_dea`、`macd_histogram` SHALL 均为 `None`（而非当前的 0.0）

#### Scenario: KDJ 数据不足
- **WHEN** 计算 KDJ(9,3,3) 但数据不足 9 根
- **THEN** `kdj_k`、`kdj_d`、`kdj_j` SHALL 均为 `None`（而非当前的 50.0）

#### Scenario: 布林带数据不足
- **WHEN** 计算布林带(20,2) 但收盘价序列不足 20 根
- **THEN** `bb_upper`、`bb_lower`、`bb_middle`、`bb_bandwidth` SHALL 均为 `None`（而非当前的 0.0）

#### Scenario: 数据充足时行为不变
- **WHEN** 各指标所需的数据量均充足
- **THEN** 指标值 SHALL 为正常计算的浮点数，行为与当前一致

---

### Requirement: Prompt 填充兼容 None 指标值
`fill_user_prompt()` 在填充技术分析 Prompt 模板时，SHALL 将 `None` 值的指标转为字符串 `"N/A"` 后再填入模板，确保 LLM 能明确识别"数据不足"的指标并忽略该条。

#### Scenario: 指标为 None 时填充 N/A
- **WHEN** `snapshot.rsi_value` 为 `None`
- **THEN** Prompt 中 `{rsi_value}` 占位符 SHALL 被替换为 `"N/A"`

#### Scenario: 指标为正常值时行为不变
- **WHEN** `snapshot.rsi_value` 为 `72.5`
- **THEN** Prompt 中 `{rsi_value}` 占位符 SHALL 被替换为 `72.5`，行为与当前一致
