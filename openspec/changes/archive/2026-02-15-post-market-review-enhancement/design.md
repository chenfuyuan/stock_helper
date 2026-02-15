## Context

当前 `market_insight` 模块已实现概念热度计算、涨停扫描归因和每日复盘报告生成，但仅覆盖基础行情维度。超短线交易的盘后复盘还需要市场情绪量化（连板梯队、炸板率、昨日涨停表现）和主力资金行为（龙虎榜、资金流向）两大数据维度。

**现有数据流**：

```
Tushare → data_engineering (ETL+落库) → Ports → market_insight (分析+报告)
```

**目标数据流**（新增 AkShare 路径）：

```
Tushare  ─→ data_engineering (基石数据)     ─→ Ports ─→ market_insight
AkShare  ─→ data_engineering (增强数据+落库) ─→ Ports ─→ market_insight
```

**约束**：
- AkShare 为免费数据源，调用需限速（避免 IP 封禁），无 Token 机制
- 数据为每日快照型（按日期查询当天全量），不同于 Tushare 的按股票分页历史同步
- `data_engineering` 已有 AkShare 概念数据客户端（`AkShareConceptClient`），可复用其限速和异步执行模式

## Goals / Non-Goals

**Goals:**
- 在 `data_engineering` 中接入 AkShare 的 5 类增强数据（涨停池、炸板池、昨日涨停表现、龙虎榜、板块资金流向），采集并落库
- 在 `market_insight` 中基于上述数据计算衍生指标（连板梯队分布、赚钱/亏钱效应、炸板率、龙虎榜席位分析、板块资金净流入排名）
- 将新数据维度整合进每日复盘报告，提供更深度的市场洞察
- 提供新的 REST API 查询端点

**Non-Goals:**
- 新闻快讯采集与事件关联（由后续独立模块承担）
- 个股级别的资金流向分析（MVP 阶段仅做板块级别）
- AkShare 数据的历史全量回填（仅支持每日增量采集）
- MI 衍生指标的独立持久化（MVP 阶段在报告生成时实时计算）

## Decisions

### D1: AkShare 客户端组织方式

**决策**：提取 `AkShareBaseClient` 基类封装限速与异步执行逻辑，新建 `AkShareMarketDataClient` 继承基类，实现新的 Provider Ports。现有 `AkShareConceptClient` 也改为继承基类。

**替代方案**：
- A. 在 `AkShareConceptClient` 中添加新方法 → 违反 SRP，概念数据与市场情绪数据职责不同
- B. 新建独立客户端，复制限速逻辑 → 代码重复，限速参数不一致风险

**理由**：基类复用进程级限速锁和 `_run_in_executor` 逻辑，子类专注于各自的 API 调用和数据转换。符合 OCP（开放封闭原则）。

### D2: Provider Port 粒度

**决策**：按领域类别划分为两个 Provider Port：
- `IMarketSentimentProvider`：涵盖涨停池、炸板池、昨日涨停表现
- `IDragonTigerProvider`：涵盖龙虎榜详情
- 板块资金流向使用 `ISectorCapitalFlowProvider` 独立接口

**替代方案**：
- A. 一个大接口包含全部 5 个方法 → 违反 ISP（接口隔离原则）
- B. 每个数据类型一个接口（5 个接口） → 过于碎片化，增加注入复杂度

**理由**：同一类别的数据在业务上高度相关（情绪类三合一），消费方通常同时需要。三个接口平衡了粒度与实用性。

### D3: 数据同步模式

**决策**：采用"日期快照同步"模式，新建 `SyncAkShareMarketDataCmd` 应用命令，接受 `trade_date` 参数，一次调用同步指定日期的所有增强数据。

**替代方案**：
- A. 集成到现有 `SyncEngine` 的 `run_history_sync` 循环 → 架构不匹配，AkShare 是按日期全量快照而非按股票分批
- B. 每种数据类型独立命令（5 个命令） → 调度繁琐，通常需要一起执行

**理由**：AkShare 的数据是日期维度的快照（传入日期返回当日全量），与 Tushare 的按股票遍历历史模式本质不同。单一命令内部按数据类型串行调用，失败单类不阻塞其余类型。新增 `SyncJobType.AKSHARE_MARKET_DATA` 用于任务状态追踪。

### D4: MI 消费 DE 数据方式

**决策**：在 `market_insight/domain/ports/` 新建数据消费 Port（`ISentimentDataPort`、`ICapitalFlowDataPort`），在 `infrastructure/adapters/` 新建适配器桥接 DE 的查询用例。遵循与现有 `DeMarketDataAdapter` / `DeConceptDataAdapter` 相同的模式。

**理由**：保持依赖倒置，MI 不直接依赖 DE 的基础设施实现，通过 Ports 解耦。

### D5: 新数据库表设计

**决策**：在 `data_engineering` 侧新增 5 张表，均使用 `de_` 前缀：

| 表名 | 用途 | 唯一约束 |
|:---|:---|:---|
| `de_limit_up_pool` | 涨停池快照（含连板天数） | `(trade_date, third_code)` |
| `de_broken_board_pool` | 炸板池快照 | `(trade_date, third_code)` |
| `de_previous_limit_up` | 昨日涨停今日表现 | `(trade_date, third_code)` |
| `de_dragon_tiger` | 龙虎榜详情 | `(trade_date, third_code, reason)` |
| `de_sector_capital_flow` | 板块资金流向 | `(trade_date, sector_name, sector_type)` |

所有表均采用 UPSERT 模式（`ON CONFLICT DO UPDATE`），支持幂等同步。

### D6: 报告增强策略

**决策**：在现有 `MarkdownReportGenerator` 中新增三个报告章节（市场情绪、龙虎榜、资金流向），插入在"涨停天梯"和"市场概览"之间。衍生指标（连板梯队分布、炸板率、赚钱效应等）由新的领域服务在报告生成流程中实时计算，不额外持久化。

**理由**：MVP 阶段避免引入额外的持久化复杂度。如后续需要情绪指标的历史趋势分析，可新增汇总表。

### D7: 分层 TDD 实现策略

**决策**：遵循 `tech-standards.md` 的分层 TDD 策略，实现节奏按层区分：

| 层级 | 策略 | 理由 |
|:---|:---|:---|
| MI Domain Services（`SentimentAnalyzer`、`CapitalFlowAnalyzer`） | **Test-First（强制）** | 纯函数式计算，无外部依赖，Spec Scenarios 可直接转为测试用例 |
| DE/MI Application Commands/Queries | **Test-First（推荐）** | Mock Port 依赖验证编排逻辑和异常隔离 |
| DE Infrastructure（`AkShareMarketDataClient`、PG Repos） | **Test-After** | 依赖外部 API/DB，先实现再编写集成测试 |
| MI Presentation（REST Router） | **Test-After** | API 端点测试需要完整服务装配 |

**替代方案**：全面 Test-After（"先实现全部再补测"）→ 失去 TDD 对 Domain 层设计的反馈价值，容易产生难以测试的耦合代码。

**理由**：Domain/Application 层的 test-first 确保领域服务在实现前就有明确的行为契约，Spec Scenarios → Test Cases → Implementation 形成闭环。Infrastructure 层因外部依赖特性不适合 test-first，但仍需 test-after 保证集成正确性。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|:---|:---|:---|
| AkShare API 不稳定 / 接口变更 | 数据采集失败，报告生成不完整 | 每个数据类型独立采集，单类失败不阻塞其余；报告中缺失数据章节标注"数据暂不可用" |
| AkShare IP 限流 / 封禁 | 大量调用后被封 | 复用进程级限速锁（默认 0.3s 间隔）；5 个 API 调用总耗时约 1.5-2s，风险低 |
| AkShare 返回数据列名变化 | Converter 解析失败 | Converter 中做防御性编程，缺失列记录 WARNING 并返回空列表 |
| 龙虎榜数据量可能较大 | 单日可能有几十到上百条记录 | 日频快照，数据量可控；使用批量 UPSERT |
| `GenerateDailyReportCmd` 编排复杂度增加 | 流程步骤从 8 步增加到 12+ 步 | 将新数据获取逻辑封装为独立的 helper 方法，保持主流程可读性 |
