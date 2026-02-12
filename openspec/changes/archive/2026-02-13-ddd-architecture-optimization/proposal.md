## Why

项目已声明 DDD + Clean Architecture 原则（见 `vision-and-modules.md`、`tech-standards.md`），但当前实现在 **依赖方向、模块隔离、组合根（Composition Root）、文件命名与单一职责** 四方面存在系统性违规。随着 Coordinator / Debate / Judge 三个新 Bounded Context 即将落地，若不先清理这些架构债务，新模块将继承同样的反模式，修复成本将指数级增长。**现在是做架构治理的最佳时机**——在新模块动工之前。

## What Changes

### A. 依赖方向与模块隔离

- **拆分 God Config**：将 `src/shared/config.py` 中模块专属配置（Tushare、LLM、Bocha、同步参数）下沉到对应 Bounded Context 的 `infrastructure/config.py`，`shared/config.py` 仅保留真正的全局配置（PROJECT_NAME、DB 连接、CORS 等）。
- **修复跨模块 Infrastructure 依赖**：`research/presentation` 直接 import `data_engineering.infrastructure` 的具体仓储实现（`pg_quote_repo`、`pg_finance_repo`），**BREAKING**——改为仅依赖 `data_engineering.application` 接口。
- **引入 Composition Root / DI 容器**：在 `src/shared/` 新增模块级 DI wiring（可采用 `dependency-injector` 或手写 Container），将散落在各 Presentation 路由文件中的 Depends 工厂收拢为统一组合根。
- **治理 `main.py` 启动依赖**：将 `main.py` 中对 `PgLLMConfigRepository`、`LLMRegistry` 的直接 import 改为通过 Application Service / DI 容器获取。
- **路由注册模块自治**：各模块 Presentation 层对外暴露统一的 `router`，`src/api/routes.py` 仅做聚合 include，不再直接引用模块内部子路由。
- **`research/agents/` 归入分层**：将 `agents/` 目录移至 `infrastructure/agents/`，保持四层结构一致。

### B. 文件命名与单一职责治理

- **DTO 从 `domain/ports/` 迁出**：`research/domain/ports/` 下的 `dto_inputs.py`、`dto_financial_inputs.py`、`dto_valuation_inputs.py` 迁移到 `research/domain/dtos/`，`ports/` 仅保留 Port 接口（ABC）。
- **拆分混合 DTO 文件**：`dto_financial_inputs.py` 混合了原始输入（`FinanceRecordInput`）与快照（`FinancialSnapshotDTO`），拆为独立文件；`dto_valuation_inputs.py` 同理。
- **统一 DTO 命名**：`dtos.py` → `technical_analysis_dtos.py`，与同级 `financial_dtos.py`、`valuation_dtos.py` 保持一致。
- **文件名与类名对齐**：`daily_bar.py`（实体类 `StockDaily`）→ 文件名或类名二选一统一。
- **消除 `PlaceholderValue` 重复**：`dto_financial_inputs.py` 和 `dto_valuation_inputs.py` 各自定义了 `PlaceholderValue` 且定义不一致，提取到公共位置。
- **Query 归位**：`data_engineering/application/commands/get_stock_basic_info.py` 是只读查询，移到 `queries/`。
- **DTO 与 UseCase 解耦**：`get_daily_bars_for_ticker.py`、`get_stock_basic_info.py` 等文件将 DTO 与 UseCase 混写，DTO 抽到 `application/dtos/` 子包。
- **DTO 不暴露领域实体**：`StockBasicInfoDTO.info` 直接引用 `StockInfo` 领域实体，改为扁平化字段或独立 DTO。

## Capabilities

### New Capabilities
- `dependency-injection-root`: 引入集中式 Composition Root / DI 容器，统一管理跨模块依赖注入，消除 Presentation 层手动 wiring。
- `module-config-isolation`: 各 Bounded Context 拥有独立的 Infrastructure Config，共享内核仅保留全局配置。
- `file-naming-srp-cleanup`: 统一文件命名规范、消除 SRP 违规、对齐 DTO 目录结构，为新模块建立干净的参考范式。

### Modified Capabilities
（无现有 spec 级别的行为变更——本次优化聚焦内部架构重构，不改变对外能力的需求定义。）

## Impact

- **受影响代码**：
  - `src/shared/config.py` — 大幅瘦身
  - `src/modules/data_engineering/infrastructure/` — 新增 `config.py`
  - `src/modules/data_engineering/application/commands/get_stock_basic_info.py` → 移到 `queries/`
  - `src/modules/data_engineering/application/queries/*.py` — DTO 抽离到 `dtos/` 子包
  - `src/modules/data_engineering/domain/model/daily_bar.py` — 文件名或类名统一
  - `src/modules/llm_platform/infrastructure/` — 新增 `config.py`
  - `src/modules/research/domain/ports/dto_*.py` → `research/domain/dtos/`（目录迁移 + 拆分）
  - `src/modules/research/domain/dtos.py` → `technical_analysis_dtos.py`（重命名）
  - `src/modules/research/presentation/rest/*.py` — 移除对 `data_engineering.infrastructure` 的直接 import，改用 DI 容器
  - `src/modules/research/agents/` → `src/modules/research/infrastructure/agents/`（目录迁移）
  - `src/main.py` — startup 逻辑改为委托 Application Service
  - `src/api/routes.py` — 简化为仅聚合各模块暴露的 router
- **API 影响**：外部 HTTP 接口无变化（纯内部重构）
- **依赖**：可能引入 `dependency-injector` 库（或选择纯手写 Container，design 阶段决定）
- **测试**：现有测试可能需要更新 import 路径；DI 容器引入后测试注入更简洁
- **风险**：import 路径变更为 **BREAKING**（内部），需在一个 PR 内完成以避免中间态；建议搭配 IDE 全局重命名 + `grep` 验证
