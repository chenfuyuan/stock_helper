# Purpose

`market_insight` 模块的每日复盘报告能力。编排完整计算流程（获取数据 → 计算热度 → 扫描涨停 → 持久化 → 生成报告），输出 Markdown 日报文件，并提供 REST API 端点用于查询和触发。

## ADDED Requirements

### Requirement: GenerateDailyReportCmd 应用命令

系统 MUST 在 `market_insight/application/commands/generate_daily_report_cmd.py` 中实现 `GenerateDailyReportCmd`。

该命令 MUST 编排以下完整流程：

1. 通过 `IMarketDataPort` 获取指定日期的全市场日线数据
2. 通过 `IConceptDataPort` 获取所有概念及其成分股映射
3. 构建 `concept_stock_map`（以 third_code 为 key 的反向索引）
4. 调用 `ConceptHeatCalculator.calculate()` 计算板块热度
5. 调用 `LimitUpScanner.scan()` 扫描涨停股
6. 通过 `IConceptHeatRepository.save_all()` 持久化热度数据
7. 通过 `ILimitUpRepository.save_all()` 持久化涨停数据
8. 调用报告生成器输出 Markdown 日报
9. 返回执行结果摘要

接口签名：

```
execute(trade_date: date) -> DailyReportResult
```

`DailyReportResult` 为 Application 层 DTO，字段 MUST 包含：

- `trade_date`（date）：交易日期
- `concept_count`（int）：参与计算的概念数量
- `limit_up_count`（int）：涨停股数量
- `report_path`（str）：生成的 Markdown 文件路径
- `elapsed_seconds`（float）：总执行耗时（秒）

#### Scenario: 正常执行日报生成

- **WHEN** 调用 `execute(date(2025, 1, 6))`，且 data_engineering 中有该日行情和概念数据
- **THEN** MUST 完成板块热度计算并持久化
- **THEN** MUST 完成涨停扫描并持久化
- **THEN** MUST 生成 Markdown 报告文件
- **THEN** 返回的 `DailyReportResult` 中 `concept_count` MUST > 0

#### Scenario: 无行情数据时的处理

- **WHEN** 调用 `execute()` 但指定日期无行情数据（非交易日）
- **THEN** MUST 返回结果，其中 `concept_count` 为 0、`limit_up_count` 为 0
- **THEN** MUST 不生成报告文件
- **THEN** MUST 记录 WARNING 级别日志

#### Scenario: 重复执行幂等

- **WHEN** 对同一日期执行两次 `execute()`
- **THEN** 数据库中的热度和涨停数据 MUST 为最新计算结果（UPSERT 覆盖）
- **THEN** Markdown 报告文件 MUST 被覆盖更新

#### Scenario: 执行结果包含耗时

- **WHEN** 命令执行完毕
- **THEN** `elapsed_seconds` MUST 反映实际执行耗时
- **THEN** 日志 MUST 记录 INFO 级别的执行摘要（概念数、涨停数、耗时）

### Requirement: MarkdownReportGenerator 报告生成器

系统 MUST 在 `market_insight/infrastructure/report/markdown_report_generator.py` 中实现 `MarkdownReportGenerator`。

该生成器 MUST 根据板块热度和涨停数据生成结构化 Markdown 文件。

输出文件路径格式：`{output_dir}/YYYY-MM-DD-market-insight.md`

报告 MUST 包含以下章节：

1. **标题**：`# 每日市场洞察 - YYYY-MM-DD`
2. **Top N 强势概念**：按 `avg_pct_chg` 降序，以表格形式展示排名、概念名称、涨跌幅、涨停家数、成交额。默认 Top 10。
3. **今日涨停天梯**：按概念分组展示涨停股。每个概念下列出涨停股名称、代码、涨跌幅。
4. **市场概览**：涨停总数、概念板块总数等统计信息。
5. **数据更新时间**：报告生成时间戳。

#### Scenario: 正常生成报告

- **WHEN** 输入包含 10 个概念热度和 20 只涨停股
- **THEN** 生成的 Markdown 文件 MUST 包含上述全部章节
- **THEN** 强势概念表格 MUST 按 avg_pct_chg 降序排列
- **THEN** 涨停天梯 MUST 按概念分组

#### Scenario: 无涨停股时的报告

- **WHEN** 输入的涨停列表为空
- **THEN** 涨停天梯章节 MUST 显示"今日无涨停"
- **THEN** 其他章节 MUST 正常生成

#### Scenario: 报告文件可覆盖

- **WHEN** 同一日期的报告文件已存在
- **THEN** MUST 覆盖已有文件

### Requirement: GetConceptHeatQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_concept_heat_query.py` 中实现 `GetConceptHeatQuery`。

接口签名：

```
execute(trade_date: date, top_n: int | None = None) -> list[ConceptHeatDTO]
```

`ConceptHeatDTO` 为 Application 层 DTO，字段 MUST 包含：

- `trade_date`（date）
- `concept_code`（str）
- `concept_name`（str）
- `avg_pct_chg`（float）
- `stock_count`（int）
- `up_count`（int）
- `down_count`（int）
- `limit_up_count`（int）
- `total_amount`（float）

#### Scenario: 查询指定日期热度

- **WHEN** 调用 `execute(date(2025, 1, 6), top_n=10)`
- **THEN** 返回该日期前 10 名概念热度 DTO 列表
- **THEN** 列表 MUST 按 `avg_pct_chg` 降序

#### Scenario: 日期无数据

- **WHEN** 调用 `execute()` 且该日期无热度数据
- **THEN** MUST 返回空列表 `[]`

### Requirement: GetLimitUpQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_limit_up_query.py` 中实现 `GetLimitUpQuery`。

接口签名：

```
execute(trade_date: date, concept_code: str | None = None) -> list[LimitUpStockDTO]
```

`LimitUpStockDTO` 为 Application 层 DTO，字段 MUST 包含：

- `trade_date`（date）
- `third_code`（str）
- `stock_name`（str）
- `pct_chg`（float）
- `close`（float）
- `amount`（float）
- `concept_codes`（list[str]）：向后兼容属性，从 concepts 对象数组中提取
- `concept_names`（list[str]）：向后兼容属性，从 concepts 对象数组中提取
- `limit_type`（str）

#### Scenario: 查询指定日期全部涨停股

- **WHEN** 调用 `execute(date(2025, 1, 6))`
- **THEN** 返回该日期全部涨停股 DTO 列表

#### Scenario: 按概念过滤涨停股

- **WHEN** 调用 `execute(date(2025, 1, 6), concept_code="BK0493")`
- **THEN** 仅返回属于该概念的涨停股

#### Scenario: 日期无涨停

- **WHEN** 调用 `execute()` 且该日期无涨停数据
- **THEN** MUST 返回空列表 `[]`

### Requirement: REST API 端点

系统 MUST 在 `market_insight/presentation/rest/market_insight_router.py` 中实现 FastAPI Router。

Router 前缀 MUST 为 `/api/market-insight`。

MUST 提供以下端点：

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/concept-heat` | GET | `trade_date: date`（必填）、`top_n: int`（可选，默认 10） | `list[ConceptHeatDTO]` |
| `/limit-up` | GET | `trade_date: date`（必填）、`concept_code: str`（可选） | `list[LimitUpStockDTO]` |
| `/daily-report` | POST | `trade_date: date`（必填） | `DailyReportResult` |

所有端点 MUST 使用 Pydantic 响应模型。

#### Scenario: GET 查询板块热度

- **WHEN** 请求 `GET /api/market-insight/concept-heat?trade_date=2025-01-06&top_n=5`
- **THEN** 返回 HTTP 200，body 为前 5 名概念热度 JSON 数组

#### Scenario: GET 查询涨停股

- **WHEN** 请求 `GET /api/market-insight/limit-up?trade_date=2025-01-06`
- **THEN** 返回 HTTP 200，body 为该日涨停股 JSON 数组

#### Scenario: GET 按概念过滤涨停股

- **WHEN** 请求 `GET /api/market-insight/limit-up?trade_date=2025-01-06&concept_code=BK0493`
- **THEN** 返回 HTTP 200，body 仅包含该概念下的涨停股

#### Scenario: POST 触发日报生成

- **WHEN** 请求 `POST /api/market-insight/daily-report?trade_date=2025-01-06`
- **THEN** 执行完整计算流程
- **THEN** 返回 HTTP 200，body 为 `DailyReportResult`

#### Scenario: 参数缺失返回 422

- **WHEN** 请求 `GET /api/market-insight/concept-heat`（缺少 trade_date）
- **THEN** 返回 HTTP 422 Validation Error

### Requirement: MarketInsightContainer DI 容器

系统 MUST 在 `market_insight/container.py` 中实现 `MarketInsightContainer`。

该容器 MUST 注册以下依赖：

- `DeConceptDataAdapter` 作为 `IConceptDataPort` 的实现
- `DeMarketDataAdapter` 作为 `IMarketDataPort` 的实现
- `PgConceptHeatRepository` 作为 `IConceptHeatRepository` 的实现
- `PgLimitUpRepository` 作为 `ILimitUpRepository` 的实现
- `ConceptHeatCalculator` 领域服务
- `LimitUpScanner` 领域服务
- `MarkdownReportGenerator` 报告生成器
- `GenerateDailyReportCmd` 应用命令
- `GetConceptHeatQuery` 查询用例
- `GetLimitUpQuery` 查询用例

容器 MUST 接受 `AsyncSession` 和 `DataEngineeringContainer` 作为构造参数。

#### Scenario: 容器正确组装依赖

- **WHEN** 通过 `MarketInsightContainer` 获取 `GenerateDailyReportCmd`
- **THEN** 命令内的所有依赖 MUST 被正确注入
- **THEN** Adapters MUST 通过 `DataEngineeringContainer` 获取上游能力

#### Scenario: Repository 可注入

- **WHEN** 通过容器请求 `IConceptHeatRepository`
- **THEN** MUST 返回 `PgConceptHeatRepository` 实例

### Requirement: vision-and-modules.md 模块注册

系统 MUST 更新 `openspec/specs/vision-and-modules.md` 的模块注册表（第 4.2 节），新增 `market_insight` 模块条目。

| 字段 | 值 |
|------|------|
| 模块 | Market Insight |
| 路径 | `src/modules/market_insight/` |
| 核心职责 | 板块维度的市场洞察分析。概念热度计算、涨停扫描归因、每日复盘报告。 |
| 对外暴露接口 | `GetConceptHeatQuery`, `GetLimitUpQuery`, `GenerateDailyReportCmd` |

同时 MUST 在上下文映射（第 3 节）中体现 `market_insight` 与 `data_engineering` 的依赖关系。

#### Scenario: 模块注册完整

- **WHEN** 查看 `vision-and-modules.md` 的模块注册表
- **THEN** MUST 包含 `market_insight` 条目
- **THEN** 模块路径 MUST 为 `src/modules/market_insight/`

#### Scenario: 依赖关系明确

- **WHEN** 查看上下文映射
- **THEN** `market_insight` → `data_engineering` 的依赖关系 MUST 被标注

### Requirement: 调用指南文档

系统 MUST 在 `docs/guides/market-insight-guide.md` 中输出模块调用指南。

文档 MUST 包含以下章节：

1. **模块概述**：功能定位、MVP 能力范围
2. **前置条件**：依赖的数据同步（概念数据、日线行情）及其触发方式
3. **CLI 用法**：命令行触发每日复盘的方式和参数
4. **HTTP API 说明**：各端点的请求/响应示例（含 curl 命令）
5. **输出说明**：Markdown 报告的位置和结构
6. **常见问题**：数据缺失、计算异常等场景的排查指南

#### Scenario: 文档存在且完整

- **WHEN** 检查 `docs/guides/market-insight-guide.md`
- **THEN** 文件 MUST 存在
- **THEN** MUST 包含上述 6 个章节

#### Scenario: API 示例可执行

- **WHEN** 复制文档中的 curl 示例执行
- **THEN** 请求格式 MUST 正确（端点、参数、HTTP 方法）
