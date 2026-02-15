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

- **WHEN** 调用 `get_sector_capital_flow` 但 DE 中无对应日期数据
- **THEN** 系统 MUST 返回空列表

---

### Requirement: CapitalFlowAnalyzer 领域服务

系统 MUST 在 `market_insight/domain/services/capital_flow_analyzer.py` 中实现 `CapitalFlowAnalyzer` 领域服务。

该服务 MUST 提供以下方法：

1. `analyze_dragon_tiger(details: list[DragonTigerItemDTO]) -> DragonTigerAnalysis`

   分析龙虎榜数据。`DragonTigerAnalysis` 字段 MUST 包含：
   - `total_count`（int）：上榜个股总数（去重后）
   - `total_net_buy`（float）：龙虎榜合计净买入额
   - `top_net_buy_stocks`（list[DragonTigerStockSummary]）：净买入前 10 的个股
   - `top_net_sell_stocks`（list[DragonTigerStockSummary]）：净卖出前 10 的个股
   - `institutional_activity`（list[DragonTigerStockSummary]）：机构席位参与的个股

   `DragonTigerStockSummary` 字段 MUST 包含：
   - `third_code`（str）、`stock_name`（str）、`pct_chg`（float）
   - `net_amount`（float）、`reason`（str）

   机构席位判定：`seat_name` 中包含"机构"关键词的席位。

2. `analyze_sector_capital_flow(flows: list[SectorCapitalFlowItemDTO], top_n: int = 10) -> SectorCapitalFlowAnalysis`

   分析板块资金流向。`SectorCapitalFlowAnalysis` 字段 MUST 包含：
   - `top_inflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流入前 N 板块
   - `top_outflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流出前 N 板块
   - `total_net_inflow`（float）：全市场板块净流入合计

   `top_inflow_sectors` MUST 按 `net_amount` 降序排列。
   `top_outflow_sectors` MUST 按 `net_amount` 升序排列。

所有分析方法 MUST 为纯函数式计算，不依赖外部 I/O。

上述结果 DTO MUST 定义在 `market_insight/domain/dtos/capital_flow_dtos.py` 中。

#### Scenario: 龙虎榜分析正常

- **WHEN** 传入 15 条龙虎榜记录（涉及 12 只个股）
- **THEN** `total_count` MUST 为 12，`top_net_buy_stocks` 最多 10 条，按净买入降序

#### Scenario: 龙虎榜包含机构席位

- **WHEN** 某个股的 `buy_seats` 中有 `seat_name` 包含"机构"的席位
- **THEN** 该个股 MUST 出现在 `institutional_activity` 列表中

#### Scenario: 龙虎榜为空

- **WHEN** 龙虎榜数据为空列表
- **THEN** `total_count` 为 0，所有子列表为空

#### Scenario: 板块资金流向排名

- **WHEN** 传入 50 个板块的资金流向数据
- **THEN** `top_inflow_sectors` MUST 返回净流入最高的 10 个板块，`top_outflow_sectors` 返回净流出最大的 10 个板块

#### Scenario: 板块资金流向为空

- **WHEN** 资金流向数据为空列表
- **THEN** 所有字段为空或 0

#### Scenario: 同一个股因多个原因上榜龙虎榜

- **WHEN** 某个股以"日涨幅偏离值达7%"和"连续三个交易日涨幅偏离值累计达20%"两条原因上榜
- **THEN** `total_count`（去重后）MUST 计为 1 只个股，但该股的净买卖额 MUST 为多条记录合计

#### Scenario: 板块资金流向数量少于 top_n

- **WHEN** 传入 5 个板块的资金流向数据，`top_n` 为 10
- **THEN** `top_inflow_sectors` 和 `top_outflow_sectors` 长度 MUST 均不超过 5（返回所有可用数据）

#### Scenario: 龙虎榜机构席位判定边界

- **WHEN** 某个股的 `buy_seats` 包含席位名称为"机构专用"和"某证券营业部"
- **THEN** 仅"机构专用"席位被识别为机构活动，该个股 MUST 出现在 `institutional_activity` 中

---

### Requirement: GetCapitalFlowAnalysisQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_capital_flow_analysis_query.py` 中实现 `GetCapitalFlowAnalysisQuery`。

接口签名：
```
execute(trade_date: date) -> CapitalFlowAnalysisDTO
```

该用例 MUST：
1. 通过 `ICapitalFlowDataPort` 获取龙虎榜和板块资金流向数据
2. 调用 `CapitalFlowAnalyzer` 计算分析结果
3. 组装并返回 `CapitalFlowAnalysisDTO`

`CapitalFlowAnalysisDTO` 为 Application 层 DTO，字段 MUST 包含：
- `trade_date`（date）
- `dragon_tiger_analysis`（DragonTigerAnalysisDTO）
- `sector_capital_flow_analysis`（SectorCapitalFlowAnalysisDTO）

Application 层 DTO MUST 定义在 `market_insight/application/dtos/capital_flow_analysis_dtos.py` 中。

#### Scenario: 正常查询资金分析

- **WHEN** 调用 `execute(date(2024, 2, 15))`，DE 中存在对应数据
- **THEN** 系统 MUST 返回包含龙虎榜和板块资金流向分析的 `CapitalFlowAnalysisDTO`

#### Scenario: 数据缺失

- **WHEN** 调用 `execute`，龙虎榜有数据但资金流向无数据
- **THEN** 系统 MUST 正常返回结果，资金流向分析各字段为空或 0
