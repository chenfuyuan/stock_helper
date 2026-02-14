# Spec: file-naming-srp-cleanup

文件命名与单一职责清理：DTO 从 `domain/ports/` 迁出到 `domain/dtos/`、混合 DTO 文件按职责拆分、文件名与主类名 snake_case 对齐、公共类型别名去重、Query/Command 目录归属修正、agents 目录归入 infrastructure。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: DTO 从 ports 目录迁出

`domain/ports/` 目录须仅包含 Port 接口（ABC 抽象类），所有 DTO 文件须迁移到 `domain/dtos/` 子包。

#### Scenario: ports 目录仅含接口

- **WHEN** 审查任意模块的 `domain/ports/` 目录
- **THEN** 目录下所有 `.py` 文件仅定义 ABC 抽象类（Port 接口），不包含 DTO、数据模型或类型别名定义

#### Scenario: Research DTO 迁移到 domain/dtos

- **WHEN** 审查 `research/domain/dtos/` 目录
- **THEN** 原 `ports/dto_inputs.py`、`ports/dto_financial_inputs.py`、`ports/dto_valuation_inputs.py` 中的 DTO 类已迁移到此目录下的独立文件中

### Requirement: 混合 DTO 文件拆分

单个文件中不得混合不同用途的 DTO（如原始输入 DTO 与聚合快照 DTO）。每个文件承担单一职责。

#### Scenario: 财务 DTO 拆分

- **WHEN** 审查 `research/domain/dtos/` 目录
- **THEN** `FinanceRecordInput`（原始输入）和 `FinancialSnapshotDTO`（聚合快照）分别位于不同的文件中（如 `financial_record_input.py` 和 `financial_snapshot.py`）

#### Scenario: 估值 DTO 拆分

- **WHEN** 审查 `research/domain/dtos/` 目录
- **THEN** `StockOverviewInput`/`ValuationDailyInput`（原始输入）和 `ValuationSnapshotDTO`（聚合快照）分别位于不同的文件中

### Requirement: DTO 文件语义化命名

DTO 文件名须体现所属能力和用途，禁止使用泛称。

#### Scenario: dtos.py 重命名

- **WHEN** 审查 `research/domain/` 目录
- **THEN** 不存在名为 `dtos.py` 的文件；原 `dtos.py` 中的技术分析 DTO 已重命名为 `technical_analysis_dtos.py`

### Requirement: 文件名与类名对齐

每个 `.py` 文件的文件名须为其主要类名的 snake_case 形式。

#### Scenario: daily_bar.py 重命名

- **WHEN** 审查 `data_engineering/domain/model/` 目录
- **THEN** 实体类 `StockDaily` 所在文件名为 `stock_daily.py`（而非 `daily_bar.py`）

### Requirement: 公共类型别名去重

跨文件复用的类型别名须提取到公共位置，禁止在多个文件中重复定义。

#### Scenario: PlaceholderValue 统一定义

- **WHEN** 在代码库中搜索 `PlaceholderValue` 的定义
- **THEN** 仅在 `research/domain/dtos/types.py`（或等效公共位置）中定义一次，所有使用方通过 import 引用，不存在重复定义

#### Scenario: PlaceholderValue 定义一致

- **WHEN** 审查 `PlaceholderValue` 的类型定义
- **THEN** 定义为 `Union[float, int, str, list[float], list[int], list[str]]`（统一包含标量和列表类型），消除原有两处定义不一致的问题

### Requirement: Query 与 Command 归属正确

`application/commands/` 仅包含写操作 UseCase；只读查询 UseCase 须归入 `application/queries/`。

#### Scenario: get_stock_basic_info 归入 queries

- **WHEN** 审查 `data_engineering/application/` 目录结构
- **THEN** `GetStockBasicInfoUseCase` 位于 `application/queries/get_stock_basic_info.py`，不在 `commands/` 下

### Requirement: agents 目录归入 infrastructure

非四层标准目录的内容须归入 `infrastructure/` 下。

#### Scenario: research agents 迁移

- **WHEN** 审查 `research/` 模块顶层目录
- **THEN** 不存在独立的 `agents/` 目录；Prompt 模板等 Agent 相关资源位于 `infrastructure/agents/` 下
