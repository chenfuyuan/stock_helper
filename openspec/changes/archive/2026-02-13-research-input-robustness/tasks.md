## 1. Adapter 空值防护（adapter-null-safety）

- [x] 1.1 在 `valuation_data_adapter.py` 中，将 `_to_stock_overview()` 改为接收完整 `basic_info_result` 并在内部检查 `daily is None`：若为 `None` 返回 `None` 并记录 WARNING 日志；`get_stock_overview()` 传播该 `None` 返回
- [x] 1.2 在 `macro_data_adapter.py` 的 `get_stock_overview()` 中，增加 `basic_info.daily is None` 检查：若为 `None` 记录 WARNING 日志并返回 `None`
- [x] 1.3 在 `catalyst_data_adapter.py` 的 `get_stock_overview()` 中，收窄 `except Exception` 为仅捕获预期的数据查询异常（如 `SQLAlchemyError`），让 `TypeError`/`AttributeError` 等编程错误向上传播
- [x] 1.4 在 `catalyst_data_adapter.py` 中，将 `industry` 默认值从 `"Unknown"` 改为 `"未知行业"`，与其他适配器保持一致
- [x] 1.5 编写测试：覆盖 `daily=None`、`daily` 正常、`industry=None` 三个场景（对 valuation / macro / catalyst 三个适配器）

## 2. 技术指标数据充分性（indicator-data-sufficiency）

- [x] 2.1 在 `technical_analyst_service.py` 中新增常量 `MIN_BARS_REQUIRED = 30`，在 `run()` 中 `bars` 非空后增加数量检查：若 `len(bars) < MIN_BARS_REQUIRED` 抛出 `BadRequestException`（message 含实际数量和门槛）
- [x] 2.2 修改 `domain/dtos/indicators_snapshot.py`：将 `rsi_value`、`macd_dif`、`macd_dea`、`macd_histogram`、`kdj_k`、`kdj_d`、`kdj_j`、`bb_upper`、`bb_lower`、`bb_middle`、`bb_bandwidth`、`atr_value`、`adx_value`、`volume_ratio`、`vwap_value` 字段类型从 `float` 改为 `Optional[float]`，默认值改为 `None`
- [x] 2.3 修改 `infrastructure/indicators/calculator.py`：各指标函数（`_rsi`、`_macd`、`_kdj`、`_bollinger`、`_atr`、`_adx`、`_vwap`）在数据不足时返回 `None` 而非 0.0/50.0；`compute_technical_indicators()` 中处理 `None` 返回值
- [x] 2.4 修改 `infrastructure/prompt_loader.py` 的 `fill_user_prompt()`：对 snapshot 中为 `None` 的指标值转为字符串 `"N/A"` 再填入模板
- [x] 2.5 编写测试：覆盖"K 线数量 < 30 时抛异常"、"数据不足时指标为 None"、"Prompt 填充中 None → N/A"三个场景

## 3. 错误处理与返回值一致性（research-error-consistency）

- [x] 3.1 修改 `catalyst_detective_service.py`：将 `StockNotFoundError` 替换为 `BadRequestException`，将 `CatalystSearchError` 替换为 `BadRequestException`；返回类型从 `CatalystDetectiveAgentResult` 改为 `dict[str, Any]`，在 `run()` 内部完成归一化
- [x] 3.2 修改 `coordinator/infrastructure/adapters/research_gateway_adapter.py`：删除 `_normalize_catalyst_result()` 方法，催化剂分支直接 `return await svc.run(symbol=symbol)`
- [x] 3.3 在 `valuation_modeler_service.py` 的 `run()` 中，`historical_valuations` 为空列表时记录 WARNING 日志（含 symbol 和时间范围），然后继续执行
- [x] 3.4 在 `financial_auditor_service.py` 的 `run()` 中，增加 `limit` 参数范围校验（1 ≤ limit ≤ 20），超出范围抛出 `BadRequestException`
- [x] 3.5 编写测试：覆盖"催化剂 Service 返回 dict"、"催化剂异常类型为 BadRequestException"、"空历史估值日线记录 WARNING"、"limit=0 抛异常"场景

## 4. 财务指标合理性校验（financial-data-sanity）

- [x] 4.1 在 `infrastructure/valuation_snapshot/snapshot_builder.py` 中定义合理性阈值常量：`GROSS_MARGIN_BOUNDS = (-100, 100)`、`ROE_BOUNDS = (-500, 500)`、`NET_MARGIN_BOUNDS = (-1000, 1000)`、`DEBT_RATIO_BOUNDS = (0, 300)`
- [x] 4.2 新增辅助函数 `_validate_financial_metric(value, bounds, metric_name, stock_code) -> PlaceholderValue`：值在范围内返回原值，超出范围返回 `"N/A"` 并记录 WARNING 日志（含字段名、原始值、stock_code）
- [x] 4.3 在 `ValuationSnapshotBuilderImpl.build()` 中，将 `gros_profit_margin`、`roe`、`net_profit_margin`、`debt_to_assets` 的赋值改为经过 `_validate_financial_metric()` 校验
- [x] 4.4 修改 `_calculate_gross_margin_trend()`：在计算趋势前校验两期 `gross_margin` 均在 `GROSS_MARGIN_BOUNDS` 范围内，任一超出则返回 `"N/A"`
- [x] 4.5 编写测试：覆盖"毛利率 44969179.57% 被替换为 N/A"、"ROE 在合理范围内正常通过"、"毛利率趋势在基础值异常时返回 N/A"、"所有指标正常时行为不变"四个场景
