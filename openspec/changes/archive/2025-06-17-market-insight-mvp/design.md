## Context

系统已具备以下数据基础：

- **概念数据**（`concept-data-source`）：`data_engineering` 通过 AkShare 获取概念板块列表 + 成分股映射，持久化至 PostgreSQL（`concept` / `concept_stock` 表）。对外暴露 `IConceptRepository`（含 `get_all_concepts_with_stocks()`）。
- **日线行情**（`de-data-sync`）：`data_engineering` 通过 TuShare 获取个股日线数据（OHLCV + 涨跌幅 + 估值），持久化至 PostgreSQL。对外暴露 `GetDailyBarsForTickerUseCase`（按个股 + 日期范围查询）。

现有模块消费模式（参考 Research / KC）：通过 `DataEngineeringContainer` 获取 UseCase 实例，在本模块 `infrastructure/adapters/` 中实现适配器转换。

**关键缺口**：当前 `data_engineering` 的日线查询仅支持「单个股票 × 日期范围」，Market Insight 需要「全市场 × 单个日期」的批量查询能力。

## Goals / Non-Goals

**Goals:**

- 新增 `market_insight` 模块（`src/modules/market_insight/`），作为独立 Bounded Context 承载板块洞察逻辑。
- 实现概念板块等权热度计算、涨停扫描归因、Markdown 日报生成三个 MVP 能力。
- 通过 Ports + Adapters 消费 `data_engineering` 数据，保持模块间解耦。
- 为后续迭代（情绪周期、龙头识别、概念轮动）预留可扩展的领域模型。

**Non-Goals:**

- 不实现连板梯队图（需历史连板数据的多日计算）。
- 不实现炸板率、晋级率等复杂情绪指标。
- 不实现 Web/GUI 界面。
- 不做流通市值加权计算（MVP 仅等权平均）。

## Decisions

### Decision 1: Market Insight 作为支撑能力层模块

**选择**：将 `market_insight` 定位为**支撑能力层 (Supporting Domain)** 模块，与 `data_engineering`、`knowledge_center` 平级。

**理由**：
- Market Insight 提供的是「板块聚合分析」数据服务，可被业务核心层（Research、Judge）消费。
- 它不直接参与「采集 → 辩论 → 决策」的核心流程，而是为决策提供辅助洞察。
- 与 Knowledge Center（知识图谱）类似，是数据二次加工能力。

**替代方案**：放在 Research 模块内部作为子功能 → 拒绝，因为 Market Insight 的板块聚合视角是独立的 Bounded Context，与 Research 的个股研报生成职责不同，耦合在一起会导致 Research 变成"上帝模块"。

### Decision 2: 通过 Application UseCase 消费 data_engineering 数据

**选择**：Market Insight 定义自己的 Domain Ports，由 Infrastructure Adapters 调用 `data_engineering` 的 Application 层 UseCase。

**具体 Ports**：
- `IConceptDataPort`：获取概念列表与成分股映射
- `IMarketDataPort`：获取指定日期的全市场日线行情

**具体 Adapters**（在 `market_insight/infrastructure/adapters/`）：
- `DeConceptDataAdapter` → 调用 `DataEngineeringContainer.get_concept_repository()`
- `DeMarketDataAdapter` → 调用新增的 `GetDailyBarsByDateUseCase`（见 Decision 3）

**理由**：遵循现有架构模式（Research 和 KC 均如此），保持模块间依赖倒置。

**替代方案**：直接 import data_engineering 的 Repository → 拒绝，违反 DDD 模块边界。

### Decision 3: 在 data_engineering 新增按日期批量查询 UseCase

**选择**：在 `data_engineering/application/queries/` 新增 `GetDailyBarsByDateUseCase`，支持按交易日期返回全市场日线数据。

```
GetDailyBarsByDateUseCase.execute(trade_date: date) -> list[DailyBarDTO]
```

同时在 `IMarketQuoteRepository` 新增方法：
```
get_all_by_trade_date(trade_date: date) -> list[StockDaily]
```

**理由**：
- 现有查询（`get_by_third_code_and_date_range`）是单股票维度，对 300+ 概念 × 数千成分股逐一查询效率极低。
- 全市场某日数据是合理的通用查询需求，其他模块未来也可能用到。
- 这是新增查询能力，不改变已有 spec 的 requirements，属于 `data_engineering` 能力的自然扩展。

**替代方案**：在 Market Insight 中直接写 SQL 查询 → 拒绝，违反模块边界。

### Decision 4: 涨停识别基于涨跌幅阈值

**选择**：通过 `pct_chg`（涨跌幅百分比）结合板块规则判断涨停，而非比对精确涨停价。

**算法**：
- 主板/中小板（代码 `0xxxxx`, `6xxxxx`）：`pct_chg >= 9.9`
- 创业板（`3xxxxx`）/科创板（`68xxxx`）：`pct_chg >= 19.8`
- ST 股票（名称含 `ST`）：`pct_chg >= 4.9`
- 北交所（`4xxxxx`, `8xxxxx`）：`pct_chg >= 29.5`（30% 涨跌幅限制）

**理由**：
- `StockDaily` 已有 `pct_chg` 字段，无需额外数据。
- 阈值法比精确计算（`close == round(pre_close * 1.1, 2)`）更宽容，能处理复权等边界情况。
- MVP 阶段此方法足够准确（误差可接受），后续可切换为精确计算。

**替代方案**：基于 `close == 涨停价` 精确计算 → 暂缓，需要考虑复权价、四舍五入规则等，MVP 不值得投入。

### Decision 5: 模块内部结构

**选择**：标准 DDD 四层结构。

```
src/modules/market_insight/
├── application/
│   ├── commands/
│   │   └── generate_daily_report_cmd.py    # 串联全流程的入口命令
│   ├── queries/
│   │   ├── get_concept_heat_query.py       # 查询板块热度
│   │   └── get_limit_up_query.py           # 查询涨停数据
│   └── dtos/
│       └── market_insight_dtos.py          # 对外暴露的 DTO
├── domain/
│   ├── model/
│   │   ├── concept_heat.py                 # 概念热度实体
│   │   ├── limit_up_stock.py               # 涨停股实体
│   │   └── enums.py                        # 领域枚举
│   ├── ports/
│   │   ├── concept_data_port.py            # 概念数据查询接口（消费 DE）
│   │   ├── market_data_port.py             # 行情数据查询接口（消费 DE）
│   │   └── repositories/
│   │       ├── concept_heat_repo.py        # 板块热度持久化接口
│   │       └── limit_up_repo.py            # 涨停数据持久化接口
│   ├── dtos/
│   │   └── insight_dtos.py                 # 领域层内部 DTO
│   ├── services/
│   │   ├── concept_heat_calculator.py      # 板块热度计算 Domain Service
│   │   └── limit_up_scanner.py             # 涨停扫描 Domain Service
│   └── exceptions.py
├── infrastructure/
│   ├── adapters/
│   │   ├── de_concept_data_adapter.py      # 适配 data_engineering 概念数据
│   │   └── de_market_data_adapter.py       # 适配 data_engineering 行情数据
│   ├── persistence/
│   │   ├── models/
│   │   │   ├── concept_heat_model.py       # ORM Model
│   │   │   └── limit_up_stock_model.py     # ORM Model
│   │   └── repositories/
│   │       ├── pg_concept_heat_repo.py     # Repository 实现
│   │       └── pg_limit_up_repo.py         # Repository 实现
│   └── report/
│       └── markdown_report_generator.py    # Markdown 报告生成器
├── presentation/
│   ├── rest/
│   │   └── market_insight_router.py        # FastAPI Router（调试 & 查询）
│   └── cli/
│       └── daily_review_cli.py             # CLI 入口（盘后触发）
└── container.py                            # DI 容器
```

**理由**：
- 计算逻辑（`concept_heat_calculator`, `limit_up_scanner`）放在 Domain Services，纯函数式计算，无外部依赖，易于单元测试。
- 报告生成放在 Infrastructure（`markdown_report_generator.py`），因为它涉及文件 I/O，属于基础设施关注点。
- 持久化层（`infrastructure/persistence/`）负责 ORM Model 和 Repository 实现，与 `data_engineering` 保持一致的结构。
- REST 层（`presentation/rest/`）提供 HTTP 调试端点，遵循现有模式。
- `GenerateDailyReportCmd` 作为 Application Command，编排完整流程：获取数据 → 计算热度 → 扫描涨停 → 持久化 → 生成报告。

### Decision 6: 计算结果持久化至 PostgreSQL

**选择**：板块热度和涨停归因数据写入 PostgreSQL，同时保留 Markdown 报告输出。

**新增表**：
- `concept_heat`：存储每日各概念板块热度数据（trade_date, concept_code, concept_name, avg_pct_chg, stock_count, up_count, down_count）。
- `limit_up_stock`：存储每日涨停股及其概念归因（trade_date, third_code, stock_name, pct_chg, concepts）。

**理由**：
- 持久化后可支撑 HTTP 查询接口，无需每次重新计算。
- 支撑历史数据对比（后续迭代：概念连续强势天数、情绪周期等）。
- 符合 Repository 模式，保持架构一致性。

**数据结构优化**：`concepts` 字段使用 JSONB 存储概念对象数组（`[{"code": "BK0001", "name": "概念A"}]`），相比分离的 `concept_codes`/`concept_names` 字段，确保数据一致性并减少存储冗余。API 层通过属性方法提供向后兼容的 `concept_codes` 和 `concept_names` 数组。

**替代方案**：仅输出 Markdown 文件 → 拒绝，无法支撑 API 查询和历史对比需求。

### Decision 7: HTTP 调试接口

**选择**：在 `presentation/rest/` 下提供 FastAPI Router，暴露以下端点：

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/market-insight/concept-heat` | GET | 查询指定日期的板块热度排名（支持 top_n、trade_date 参数） |
| `/api/market-insight/limit-up` | GET | 查询指定日期的涨停股列表（支持按概念过滤） |
| `/api/market-insight/daily-report` | POST | 触发指定日期的每日复盘计算 |

**理由**：
- 开发阶段可通过 HTTP 快速验证计算结果，无需查看 Markdown 文件或直接查库。
- 遵循现有模式（`data_engineering` 已有 REST 端点）。
- POST 触发端点便于调试和手动补算历史数据。

### Decision 8: 调用指南文档

**选择**：在 `docs/guides/` 下输出 `market-insight-guide.md`，包含模块概述、CLI 用法、HTTP API 说明和常见问题。

**理由**：便于团队成员和后续开发快速上手，降低维护成本。

## Risks / Trade-offs

- **[批量查询性能]** 全市场某日日线数据量约 5000 条 → 单次查询返回量可控。但若概念成分股有重叠（多个概念含同一只股票），同一股票的数据会被多次使用 → **缓解**：在计算层用 `dict[third_code, StockDaily]` 做内存索引，避免重复查询。

- **[涨停阈值误判]** 基于 `pct_chg` 阈值的涨停判断可能误判（如新股首日不设涨跌幅限制、复牌股无涨跌幅限制），MVP 容忍少量误差 → **缓解**：后续迭代可引入精确涨停价计算或接入涨停专用数据源。

- **[概念数据时效性]** 概念成分股映射依赖 `data_engineering` 的同步周期，若同步不及时会导致分析数据滞后 → **缓解**：`GenerateDailyReportCmd` 执行前可选择性触发概念同步，或在报告中标注数据更新时间。

- **[data_engineering 耦合]** 新增 `GetDailyBarsByDateUseCase` 涉及修改 `data_engineering` 模块代码 → **缓解**：这是纯新增（new query），不改变已有接口契约，风险可控。

- **[数据库 Migration 复杂度]** 新增 `concept_heat` 和 `limit_up_stock` 两张表，需要 Alembic Migration → **缓解**：表结构简单，无外键关联，Migration 风险低。

- **[重复计算防护]** 同一日期重复触发计算可能导致数据重复 → **缓解**：Repository 采用 UPSERT 策略（以 trade_date + concept_code / third_code 为唯一键），保证幂等性。
