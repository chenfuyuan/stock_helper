## Why

超短线选手每日复盘需要快速回答两个核心问题：**"今天什么板块强？"** 和 **"哪些票涨停了？"**。目前系统缺少板块维度的聚合分析能力——`data_engineering` 模块已具备概念数据获取（`concept-data-source`）和个股日线行情的能力，但尚无将二者结合进行板块热度计算、涨停归因和结构化输出的业务模块。

Market Insight 作为新的 Bounded Context，填补「原始数据 → 板块洞察」的空白，为后续情绪周期分析、龙头识别、概念轮动等高级功能奠定基础。MVP 先跑通最小闭环，验证数据管道和计算逻辑的可行性。

## What Changes

- **新增 `market_insight` 模块**（`src/modules/market_insight/`）：遵循 DDD 分层结构，作为独立 Bounded Context 承载板块洞察业务逻辑。
- **概念板块热度计算**：基于等权平均法聚合概念成分股涨跌幅，输出板块热度排名（Top N 强势概念）。
- **涨停扫描与概念归因**：识别当日涨停个股，映射回所属概念板块，输出概念维度的涨停统计。
- **计算结果持久化**：板块热度与涨停归因数据写入 PostgreSQL，支撑历史查询与 API 服务。
- **每日复盘报告生成**：汇总板块热度与涨停数据，自动生成结构化 Markdown 复盘日报。
- **HTTP 调试接口**：提供 REST API 端点，用于查询板块热度、涨停数据，便于开发调试和集成验证。
- **调用指南文档**：在 `docs/` 下输出模块使用与接口调用指南。
- **更新 `vision-and-modules.md`**：在模块注册表中注册 `market_insight` 模块，明确其 Bounded Context 职责与依赖关系。

## Capabilities

### New Capabilities

- `market-insight-concept-heat`: 概念板块热度计算——从 `data_engineering` 获取概念成分股与日线行情，等权平均聚合板块涨跌幅，输出板块热度排名。
- `market-insight-limit-scan`: 涨停扫描与概念归因——识别当日涨停个股（收盘价 == 涨停价），将涨停股映射至所属概念，统计各概念涨停家数。
- `market-insight-daily-report`: 每日复盘报告——消费热度排名与涨停归因数据，持久化至 PostgreSQL，并生成包含「Top 10 强势概念」和「涨停天梯」的 Markdown 日报文件；提供 REST API 端点用于查询。

### Modified Capabilities

（无。Market Insight 通过 Ports 消费 `data_engineering` 已有能力，不改变其现有 spec 的 requirements。）

## Impact

- **新模块**：`src/modules/market_insight/`（application / domain / infrastructure 全套 DDD 分层）。
- **架构文档**：`openspec/specs/vision-and-modules.md` 需新增 Market Insight 模块注册条目。
- **模块依赖**：`market_insight` → `data_engineering`（通过 Ports 获取概念列表、成分股映射、个股日线行情数据）。
- **外部依赖**：无新增——AkShare 和 TuShare 的调用均由 `data_engineering` 模块承担。
- **数据库**：新增表存储板块热度与涨停归因数据，需要 Alembic Migration。
- **REST API**：新增 FastAPI Router，提供板块热度查询、涨停数据查询端点。
- **文档**：`docs/` 下新增模块调用指南。
- **测试**：每个 capability 的 spec scenario 须有对应自动化测试，聚合计算和涨停识别逻辑以单元测试为主。
