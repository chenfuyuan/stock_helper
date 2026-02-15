# Spec: capital-flow-analysis

市场主力资金行为分析能力，涵盖龙虎榜数据解析（机构/游资席位净买卖）、板块/个股维度的资金净流入估算，为超短线交易提供资金流向洞察。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: ICapitalFlowDataPort 接口定义

系统 MUST 在 `market_insight/domain/ports/capital_flow_data_port.py` 中定义 `ICapitalFlowDataPort` ABC 接口，用于从 `data_engineering` 消费资金行为数据。

该接口 MUST 包含以下方法：

- `get_dragon_tiger(trade_date: date) -> list[DragonTigerItemDTO]`：获取指定日期的龙虎榜详情
- `get_sector_capital_flow(trade_date: date, sector_type: str | None = None) -> list[SectorCapitalFlowItemDTO]`：获取指定日期的板块资金流向

所有方法 MUST 为异步方法（async）。

`DragonTigerItemDTO` 字段 MUST 包含：
- `third_code`（str）、`stock_name`（str）、`pct_chg`（float）、`close`（float）
- `reason`（str）：上榜原因
- `net_amount`（float）：净买入额
- `buy_amount`（float）：买入总额
- `sell_amount`（float）：卖出总额
- `buy_seats`（list[dict]）：买入席位详情
- `sell_seats`（list[dict]）：卖出席位详情

`SectorCapitalFlowItemDTO` 字段 MUST 包含：
- `sector_name`（str）：板块名称
- `sector_type`（str）：板块类型
- `net_amount`（float）：净流入额（万元）
- `inflow_amount`（float）：流入额（万元）
- `outflow_amount`（float）：流出额（万元）
- `pct_chg`（float）：板块涨跌幅

DTO MUST 定义在 `market_insight/domain/dtos/capital_flow_dtos.py` 中，不直接引用 `data_engineering` 的类型。

#### Scenario: Port 在 Market Insight Domain 层定义

- **WHEN** 检查 `ICapitalFlowDataPort` 的定义位置
- **THEN** MUST 位于 `market_insight/domain/ports/capital_flow_data_port.py`
- **THEN** 返回类型 MUST 使用 `market_insight` 领域层 DTO

---

### Requirement: DeCapitalFlowDataAdapter 适配器实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_capital_flow_data_adapter.py` 中实现 `DeCapitalFlowDataAdapter`，实现 `ICapitalFlowDataPort` 接口。

该适配器 MUST 通过 `DataEngineeringContainer` 获取以下查询用例并调用：
- `GetDragonTigerByDateUseCase` → 转换为 `DragonTigerItemDTO`
- `GetSectorCapitalFlowByDateUseCase` → 转换为 `SectorCapitalFlowItemDTO`

MUST 将 `data_engineering` 的领域实体转换为 `market_insight` 的领域层 DTO。

#### Scenario: 正常获取龙虎榜数据

- **WHEN** 调用 `get_dragon_tiger(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 DE 查询用例获取数据并转换为 `list[DragonTigerItemDTO]`

#### Scenario: DE 查询无数据

- **WHEN** 调用 `get_dragon_tiger` 但 DE 中无对应日期数据
- **THEN** 系统 MUST 返回空列表

---

### Requirement: CapitalFlowAnalyzer 领域服务

系统 MUST 在 `market_insight/domain/services/capital_flow_analyzer.py` 中实现 `CapitalFlowAnalyzer` 领域服务。

该服务 MUST 提供以下方法：

1. `analyze_dragon_tiger(dragon_tiger_data: list[DragonTigerItemDTO]) -> DragonTigerAnalysis`

   分析龙虎榜数据。`DragonTigerAnalysis` 字段 MUST 包含：
   - `total_count`（int）：上榜股票总数
   - `net_buy_count`（int）：净买入股票数
   - `net_sell_count`（int）：净卖出股票数
   - `total_net_amount`（float）：净买入总额
   - `institution_net_amount`（float）：机构席位净买入额
   - `hot_money_net_amount`（float）：游资席位净买入额
   - `top_net_buys`（list[DragonTigerStockSummary]）：净买入前 5 名
   - `top_net_sells`（list[DragonTigerStockSummary]）：净卖出前 5 名

   `DragonTigerStockSummary` 字段 MUST 包含：
   - `third_code`（str）：股票代码
   - `stock_name`（str）：股票名称
   - `net_amount`（float）：净买入额
   - `reason`（str）：上榜原因

2. `analyze_sector_capital_flow(sector_flow_data: list[SectorCapitalFlowItemDTO]) -> SectorCapitalFlowAnalysis`

   分析板块资金流向。`SectorCapitalFlowAnalysis` 字段 MUST 包含：
   - `total_inflow`（float）：总流入额
   - `total_outflow`（float）：总流出额
   - `net_inflow`（float）：净流入额
   - `net_inflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流入板块列表（按净流入额降序）
   - `net_outflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流出板块列表（按净流出额降序）
   - `top_inflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流入前 10 名
   - `top_outflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流出前 10 名

所有分析方法 MUST 为纯函数式计算，不依赖外部 I/O。

上述结果 DTO MUST 定义在 `market_insight/domain/dtos/capital_flow_dtos.py` 中。

#### Scenario: 龙虎榜分析正常

- **WHEN** 龙虎榜数据包含 10 只股票，其中 6 只净买入、4 只净卖出，机构席位净买入 5000 万，游资席位净卖出 2000 万
- **THEN** `total_count` MUST 为 10，`net_buy_count` 为 6，`net_sell_count` 为 4，`institution_net_amount` 为 50000000.0，`hot_money_net_amount` 为 -20000000.0

#### Scenario: 机构席位识别

- **WHEN** 龙虎榜买入席位包含"机构专用"、"机构专用1"等名称
- **THEN** 这些席位 MUST 被识别为机构席位，计入 `institution_net_amount`

#### Scenario: 龙虎榜为空

- **WHEN** 龙虎榜数据为空列表
- **THEN** `total_count` 为 0，`total_net_amount` 为 0.0，`top_net_buys` 和 `top_net_sells` 为空列表

#### Scenario: 板块资金流向排名

- **WHEN** 板块资金流向数据包含 20 个板块，其中 12 个净流入、8 个净流出
- **THEN** `net_inflow_sectors` MUST 包含 12 个板块，`net_outflow_sectors` MUST 包含 8 个板块，`top_inflow_sectors` MUST 包含净流入前 10 名

#### Scenario: 资金流向为空

- **WHEN** 板块资金流向数据为空列表
- **THEN** `total_inflow`、`total_outflow`、`net_inflow` 均为 0.0，所有列表字段为空

#### Scenario: 机构游资席位分类

- **WHEN** 席位名称包含"机构"、"社保"、"基金"等关键词
- **THEN** 这些席位 MUST 被归类为机构席位
- **WHEN** 席位名称包含"营业部"、"证券"、"游资"等关键词
- **THEN** 这些席位 MUST 被归类为游资席位

#### Scenario: 龙虎榜汇总计算

- **WHEN** 计算龙虎榜汇总数据
- **THEN** `total_net_amount` MUST 等于所有股票 `net_amount` 的总和
- **THEN** `institution_net_amount` MUST 等于所有机构席位的净买卖差额
- **THEN** `hot_money_net_amount` MUST 等于所有游资席位的净买卖差额

#### Scenario: 板块资金流向汇总

- **WHEN** 计算板块资金流向汇总
- **THEN** `total_inflow` MUST 等于所有板块 `inflow_amount` 的总和
- **THEN** `total_outflow` MUST 等于所有板块 `outflow_amount` 的总和
- **THEN** `net_inflow` MUST 等于 `total_inflow - total_outflow`

---

### Requirement: GetCapitalFlowAnalysisQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_capital_flow_analysis_query.py` 中实现 `GetCapitalFlowAnalysisQuery`。

接口签名：
```
execute(trade_date: date, sector_type: str | None = None) -> CapitalFlowAnalysisDTO
```

该用例 MUST：
1. 通过 `ICapitalFlowDataPort` 获取龙虎榜和板块资金流向数据
2. 调用 `CapitalFlowAnalyzer` 计算各项分析指标
3. 组装并返回 `CapitalFlowAnalysisDTO`

`CapitalFlowAnalysisDTO` 为 Application 层 DTO，字段 MUST 包含：
- `trade_date`（date）
- `dragon_tiger_analysis`（DragonTigerAnalysisDTO）：龙虎榜分析
- `sector_capital_flow_analysis`（SectorCapitalFlowAnalysisDTO）：板块资金流向分析

Application 层 DTO MUST 定义在 `market_insight/application/dtos/capital_flow_analysis_dtos.py` 中。

#### Scenario: 正常查询资金流向分析

- **WHEN** 调用 `execute(date(2024, 2, 15))`，DE 中存在对应数据
- **THEN** 系统 MUST 返回包含龙虎榜和板块资金流向分析的 `CapitalFlowAnalysisDTO`

#### Scenario: 部分数据缺失

- **WHEN** 调用 `execute`，龙虎榜有数据但板块资金流向无数据
- **THEN** 系统 MUST 正常返回结果，板块资金流向分析中各字段为默认值

#### Scenario: 按板块类型过滤

- **WHEN** 调用 `execute(date(2024, 2, 15), sector_type="概念资金流")`
- **THEN** 系统 MUST 在板块资金流向分析中仅包含"概念资金流"类型的数据
