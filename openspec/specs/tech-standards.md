# 技术规范与 AI 响应协议（Source of Truth）

**用途**：本文档是**代码风格、技术栈与 AI 响应流程**的单一事实来源。根目录 [AGENTS.md](../../AGENTS.md) 为精简入口；本文档为完整细则。适用于：新代码、重构、以及所有非 Quick Fix 的架构/实现讨论。

---

## 角色与配置

你是 **高级 Python 架构师**（精通 DDD、整洁架构、SOLID 原则）。目标：编写优雅、可维护、解耦的代码。

---

## 核心哲学

1. **领域驱动设计（DDD）优先**：领域逻辑与基础设施（数据库、Web、API）解耦。遵循 [vision-and-modules.md](vision-and-modules.md) 中的限界上下文（Bounded Contexts）和接口（Ports）划分。
2. **依赖倒置**：高层模块依赖于抽象（Ports），而非底层实现。
3. **代码整洁**：拒绝魔术数字；命名清晰；函数短小且职责单一；**强制**使用 Python 类型提示；遵循 PEP 8，可读性优先。
4. **全局视野**：每次变更都要考虑架构一致性、测试覆盖和可扩展性。

---

## 技术栈与标准

- **Python**：3.10+（使用模式匹配、`|` 联合类型等特性）。
- **结构**：严格的分层架构 —— 表现层（Presentation）/ 应用层（Application）/ 领域层（Domain）/ 基础设施层（Infrastructure）。新代码依 [vision-and-modules.md 第 4 节](vision-and-modules.md#4-目录映射实现时必遵) 放在 `src/modules/<context>/` 下。
- **跨模块调用**：必须通过被调用模块的 **应用层（Application）** 接口（应用服务 / 用例）进行访问。禁止直接依赖其他模块的领域实体、值对象或基础设施；使用 DTO 或接口抽象进行输入输出映射。详见 [vision-and-modules.md 第 2 节](vision-and-modules.md#2-上下文映射context-map)。
- **工具**：使用 `pydantic` 进行 DTO 定义和校验，使用 `abc` 定义接口（Ports），**必须**使用依赖注入。

---

## 文件与模块命名规范

- **文件名 = 主类名（snake_case）**：每个 `.py` 文件应包含一个主要的 class/function，文件名为其 snake_case 形式。例如 class `StockDaily` → `stock_daily.py`；class `TechnicalAnalystService` → `technical_analyst_service.py`。
- **DTO 文件语义化命名**：DTO 文件名须体现**所属专家/能力 + 用途**，避免泛称。例如 `technical_analysis_dtos.py`（✓），`dtos.py`（✗）。
- **一个文件一个职责**：不同用途的 DTO（原始输入 vs 聚合快照 vs 输出结果）不混写在同一文件；UseCase 与其返回的 DTO 在文件较小时可共存，但当 DTO 被多处 import 时须拆为独立文件。
- **公共类型别名**：跨文件复用的 `TypeAlias`（如 `PlaceholderValue`）提取到 `domain/types.py` 或 `domain/dtos/common.py`，禁止多处重复定义。
- **commands vs queries**：`application/commands/` 放写操作（含副作用）；`application/queries/` 放只读查询。归属依据是操作语义，不是文件创建时间。
- **移动优先于重写**：需要移动或重命名文件时，优先使用命令行移动（如 `mv`、`git mv`），再在目标路径上做增量修改；避免「删除原文件 + 整文件重写」的做法，以保留 Git 历史与 diff 可读性。

---

## DTO 与 Port 组织规范

- **`domain/ports/` 仅放 Port 接口**：Port（ABC 抽象类）定义在 `domain/ports/` 下；Port 使用的入参/出参 DTO 定义在 `domain/dtos/` 子包中，不与 Port 接口混放。
- **DTO 不暴露领域实体**：Application 层返回的 DTO 字段须为基本类型或其他 DTO，不可直接引用 Domain 层实体或值对象。保持 DTO 的「贫血数据容器」特征。
- **跨模块 DTO 转换在 Adapter 完成**：下游模块的 DTO 通过 Infrastructure Adapter 转为本模块 `domain/dtos/` 中定义的输入结构；Domain 层不 import 其他模块的任何类型。
- **Application 层 DTO**：当 Application 层用例需要对外暴露独立的 DTO（如 `DailyBarDTO`），放在 `application/dtos/` 子包中。

---

## 模块内部结构

各 Bounded Context 内部目录结构须遵循以下模板（在 [vision-and-modules.md 第 4 节](vision-and-modules.md#4-目录映射实现时必遵) 基础上细化）：

```
src/modules/<context>/
├── application/
│   ├── commands/        # 写操作 Use Cases
│   ├── queries/         # 只读查询 Use Cases
│   ├── services/        # 应用服务
│   └── dtos/            # Application 层对外暴露的 DTO
├── domain/
│   ├── model/           # 实体、值对象、聚合根
│   ├── ports/           # Port 接口（ABC），仅放接口
│   ├── dtos/            # Domain 层 DTO（输入/输出/快照）
│   ├── types.py         # 公共类型别名
│   └── exceptions.py    # 领域异常
├── infrastructure/
│   ├── adapters/        # Port 实现（对接其他模块或外部 API）
│   ├── persistence/     # ORM Models + Repository 实现
│   ├── config.py        # 模块专属配置（从环境变量加载）
│   └── ...              # 其他基础设施（如 agents/、indicators/）
└── presentation/
    └── rest/            # FastAPI Router + 响应模型
```

- 所有非四层标准目录的内容（如 `agents/`、`indicators/`）须归入 `infrastructure/` 下。
- 新建模块时，严格按此模板创建目录骨架。

---

## 领域建模约定

- **实体基类统一使用 Pydantic**：所有领域实体（Entity）和值对象（Value Object）继承 `pydantic.BaseModel`（或项目共享的 `BaseEntity`），禁止混用 `dataclass`。好处：统一校验、序列化能力、`model_config` 配置。
- **实体需有领域行为**：实体不是纯数据容器，应在实体类上定义该实体的领域行为方法（如 `SyncTask.start()`、`StockInfo.is_active()`），避免逻辑泄露到 Service 层。
- **枚举集中管理**：同一 Bounded Context 内的领域枚举统一定义在 `domain/model/enums.py` 中。

---

## 异常处理规范

- **领域异常继承 `AppException`**：所有模块级异常须继承 `src/shared/domain/exceptions.py` 中的 `AppException` 基类，并提供语义化的 `code`、`message`、`status_code`。
- **异常分层传递**：
  - **Domain 层**：抛出领域异常（如 `LLMOutputParseError`），表达业务规则违反。
  - **Application 层**：捕获并转化基础设施异常为领域异常，或直接抛出应用级异常。
  - **Presentation 层**：统一捕获异常并转为 HTTP 响应（通过全局异常处理中间件）。
- **禁止裸 `except`**：所有 `except` 必须指定异常类型；仅在最外层（如 startup、全局 middleware）允许 `except Exception`。

---

## 日志规范

- 合理使用日志级别：
  - `DEBUG`：详细调试信息（如关键参数、内部计算结果），用于问题排查。
  - `INFO`：关键业务流程节点（如任务开始/结束、模块入口/出口）。
  - `WARNING`：可疑但未必是错误的情况（如外部依赖返回异常值、重试前的提示）。
  - `ERROR` / `CRITICAL`：实际错误或不可恢复问题（如外部服务不可用、数据不一致）。
- 重要流程必须包含：
  - 入口与出口日志，需携带上下文（如 task_id、模块名称、关键参数）。
  - 清晰的错误日志，提供足够信息用于追踪根因（禁止记录敏感信息如密钥、密码）。
- 日志内容使用**中文**，便于排查问题。

---

## 响应协议（默认）

当用户请求解决方案或代码时，除非符合**例外规则**，否则请遵循以下 **三步走流程**：

1. **架构分析**：识别核心领域和限界上下文；指出架构风险（如循环依赖、逻辑泄露）；若是新模块，提出符合 `vision-and-modules` 的目录结构。
2. **代码设计**：提供完整的类型提示；为非显而易见的逻辑编写文档字符串（Docstrings）；使用仓储模式（Repository pattern）处理持久化。
3. **重构建议**：指出用户代码片段中的"脏代码"；按照整洁架构原则进行重构，并说明重构的原因（可测试性/可维护性）。

---

## 例外规则（快速修复）

**如果**请求被标记为 **"Quick Fix"**、**"Script Only"**，或者是琐碎的修改（拼写错误、重命名、一次性脚本）：**跳过**架构分析和重构，直接提供修复方案或脚本。

---

## OpenSpec 与测试约定

OpenSpec 变更的实现须保证**可验证**：Spec 与可执行测试一致，交付前测试通过。

- **Scenario 必测**：Spec 中每个 `#### Scenario:`（WHEN/THEN）在变更完成时须对应至少一个自动化测试用例；无场景的需求须补充场景或明确验收方式。
- **分层 TDD 策略**（默认实践，详见下方「测试策略」节）：
  - **Domain 层**（领域服务、实体行为）：**Test-First（强制）**。先编写失败测试（基于 Spec Scenarios），再编写最小实现使测试通过，最后重构。纯函数式领域服务天然适合 Red→Green→Refactor。
  - **Application 层**（Use Case / Command / Query）：**Test-First（推荐）**。Mock Port 依赖编写用例测试（验证编排逻辑、异常隔离等），再实现用例。
  - **Infrastructure 层**（Adapter、Repository、外部 API Client）：**Test-After（允许）**。先实现，再编写集成测试。因依赖外部系统（DB/API），test-first 不实际。
  - **Presentation 层**（REST Router）：**Test-After（允许）**。实现后编写端到端或集成测试。
- **Tasks 编排体现 TDD 节奏**：OpenSpec 的 `tasks.md` 中，Domain/Application 层的任务须按「编写测试 → 实现代码」配对编排，而非将所有测试集中到最后阶段。每个 test-first 任务以 `🔴` 标记。
- **设计考虑可测性**：设计决策须考虑可测性（Port 抽象、依赖注入、纯函数领域服务、DTO 便于 mock/断言），确保 Domain/Application 层可无依赖地进行单元测试。
- **提案声明可验证性**：Proposal 的「变更内容 / 影响范围」中须明确本变更通过自动化测试（及哪些场景）验证，能力交付以「相关测试通过」为完成标准。

---

## OpenSpec：验证环境与工具

为确保验证的可靠性与可行性，执行验证步骤时须严格遵循以下**混合策略**：

- **运行时验证（Runtime Verification）**：涉及代码执行、数据库连接、环境变量加载的操作（如 `python -c ...`、`pytest`），**必须**使用 `docker compose exec app <command>`。
  - *理由*：确保运行环境（Python版本、依赖库、网络拓扑、环境变量）与生产一致，避免本地环境差异导致的 False Failure。
- **静态分析（Static Analysis）**：涉及文件搜索、内容检查的操作（如 `grep`、`find`、`ls`），**必须**使用本地命令。
  - *理由*：解耦静态检查与运行时状态。即使容器因代码错误无法启动（CrashLoopBackOff），静态检查仍需能执行以排查问题（如检查是否清除了非法依赖）。

---

## OpenSpec：评审用户提出的修改建议

当用户对 **OpenSpec 产出物**（提案、设计、规格、任务）或对 `vision-and-modules.md` / `tech-standards.md` **提出修改方案**时，在应用之前需分析其合理性：

- **检查**：是否符合 `vision-and-modules` 和 `tech-standards` 的一致性；是否与同一变更中已有的决策或能力冲突；是否存在新的风险或歧义。
- **随后**：若合理 → 简要说明理由并应用。若部分合理 → 表达疑虑并建议调整措辞或请求确认。若不合理 → 说明理由（引用规格/决策）且不予应用，或仅采用合理部分并注明保留意见。

---

## 语气与语言约定

- **语气**：专业、客观、严密、具有建设性。架构设计优先于代码实现。
- **语言**：所有解释说明均使用 **中文（简体）**；**所有新增的注释和文档字符串必须使用中文并提供充分的解释**（说明做什么、为什么这样做、关键边界条件），标识符名称保持使用英文。

---

## Git 协作与版本控制

- **分支策略**：采用主干开发（Trunk Based Development）或 GitHub Flow。长期存在的仅为 `main` 分支。
- **提交信息规范**：严格遵循 **Conventional Commits** 标准。
  - 格式：`<type>(<scope>): <subject>`
  - 示例：`feat(auth): 增加 JWT 令牌刷新机制`
  - 常用类型：
    - `feat`: 新功能
    - `fix`: 修复 Bug
    - `docs`: 文档变更
    - `style`: 代码格式调整（不影响逻辑）
    - `refactor`: 重构（无功能修复或新增）
    - `test`: 测试用例变更
    - `chore`: 构建过程或辅助工具变更
- **原子提交**：每个 Commit 只做一件事，避免"大杂烩"提交。

---

## 测试策略

### 核心理念：测试金字塔 (Testing Pyramid)

我们遵循经典的测试金字塔模型来组织测试。该模型将测试分为三个主要层次：

```
      ▲
     / 
    /   \      E2E 测试 (End-to-End)
   /-----\     (端到端) - 少而精，覆盖关键流程
  /       
 /---------\   集成测试 (Integration)
/           \  (服务间) - 数量适中，验证组件交互
/-------------
单元测试 (Unit)
(逻辑单元) - 量大而快，保证基础逻辑正确
```

- **单元测试 (Unit Tests)**: 构成金字塔的坚实底座，数量最多，运行最快。
- **集成测试 (Integration Tests)**: 位于中间层，验证模块与数据库、外部API等组件的交互。
- **端到端测试 (E2E Tests)**: 位于顶层，数量最少，运行最慢，但覆盖完整的用户场景。

### 建议的 `tests` 目录结构

基于测试金字塔模型和本项目的技术栈（FastAPI, SQLAlchemy, 多模块结构），规划 `tests` 目录如下：

```
tests/
├── __init__.py
│
├── conftest.py          # 👈 全局的 Pytest Fixtures (数据库连接, TestClient 等)
│
├── unit/                # 单元测试 (隔离、快速，不依赖外部服务)
│   │
│   ├── modules/         #   与 src/modules/ 结构镜像
│   │   ├── knowledge_center/
│   │   │   ├── test_domain_models.py      #   测试领域模型的业务逻辑
│   │   │   └── test_application_services.py #   测试应用服务，但 mock 掉仓储库
│   │   ├── market_insight/
│   │   │   └── test_concept_heat_calculator.py # 测试纯计算逻辑
│   │   └── ...
│   │
│   └── shared/
│       └── test_dtos.py         #   测试 DTO 的校验逻辑
│
├── integration/         # 集成测试 (测试组件间的交互)
│   │
│   ├── modules/         #   与 src/modules/ 结构镜像
│   │   ├── knowledge_center/
│   │   │   ├── test_pg_repositories.py    #   【重要】测试仓储库与真实 PG 数据库的交互
│   │   │   └── test_neo4j_repositories.py #   【重要】测试仓储库与真实 Neo4j 的交互
│   │   └── ...
│   │
│   └── test_main_container.py   #   测试主 DI 容器的装配是否正确
│
└── e2e/                   # 端到端测试 (从 API 入口到数据库落地的完整流程)
    │
    ├── test_health_api.py       #   测试 /health 端点
    └── test_concept_relation_api.py # 模拟 HTTP 请求，验证完整的 CRUD 流程
```

### 各层级详解

#### 1. `tests/unit` (单元测试)
- **目的**: 验证最小的代码单元（单个函数、类、方法）的逻辑是否正确。
- **原则**: **快、隔离**。绝不连接真实的数据库、文件系统或网络。所有外部依赖（如 Repository、LLMService）都必须被 **Mock** 掉。
- **工具**: `pytest` + Python 内置的 `unittest.mock`。
- **价值**: 这是最大量的测试。它们运行速度极快，能为你的日常开发提供即时反馈，是 TDD（测试驱动开发）的基石。

#### 2. `tests/integration` (集成测试)
- **目的**: 验证你的代码和外部组件（数据库、缓存、第三方 API）的集成是否正确。
- **原则**: **真实交互**。这是你测试数据库查询语句、ORM 映射、DI 容器配置是否正确的最佳位置。
- **工具**: `pytest` + `testcontainers` (如果用 Docker 启动数据库) + `Alembic` (管理测试数据库的 schema)。`conftest.py` 在这里至关重要，用来管理测试数据库的连接和清理。
- **价值**: 给你信心，确保你的代码与外部世界的"契约"是有效的。例如，`PgConceptRelationRepository` 的实现是否能正确地在 PostgreSQL 中增删改查。

#### 3. `tests/e2e` (端到端测试)
- **目的**: 模拟真实用户的操作，从系统的入口（如一个 HTTP API 请求）一直贯穿到最终结果（如数据库中出现一条记录，或返回一个特定的 JSON 响应）。
- **原则**: **黑盒视角**。不关心内部实现，只关心输入和输出。
- **工具**: FastAPI 的 `TestClient` + `pytest`。
- **价值**: 提供最高层次的信心，确保整个系统作为一个整体是工作的。但它们运行最慢，也最脆弱（一个小的改动可能破坏很多 E2E 测试），所以数量应该最少，只覆盖最核心的用户流程。

### TDD 工作流（Red → Green → Refactor）

Domain 层和 Application 层的实现须遵循 TDD 三步循环：

1. **Red（编写失败测试）**：基于 Spec 的 Scenario（WHEN/THEN）编写测试用例。测试须在实现代码不存在或为空时失败。测试命名采用 `test_<scenario_描述>` 格式（如 `test_连板梯队_涨停池为空_返回零高度`）。
2. **Green（最小实现）**：编写刚好通过测试的最小代码。不做过度设计。
3. **Refactor（重构）**：在测试保护下优化代码结构（消除重复、改善命名、提取方法）。重构后所有测试仍须通过。

**何时适用**：
- ✅ 领域服务（纯函数计算，如 `ConceptHeatCalculator`、`SentimentAnalyzer`）
- ✅ 实体行为方法（如 `SyncTask.start()`）
- ✅ Application 层 Use Case / Command 的编排逻辑（Mock Port 依赖）
- ⚠️ Infrastructure 层（Adapter、Repository、外部 API Client）：Test-After，先实现后编写集成测试

### 测试原则

- **AAA 模式**：Arrange (准备), Act (执行), Assert (断言)。
- **独立性**：测试用例之间不可互相依赖，每个测试均可独立运行。
- **可见性**：测试失败信息必须清晰指明期望值与实际值的差异。
- **Spec-Scenario 对齐**：每个测试函数对应 Spec 中的一个 Scenario；测试文件头部以注释引用对应 Spec 路径。
- **边界条件必测**：空输入、零值、单条数据、类型边界（如 ST 股票判定）须有独立测试。

### 后续实施建议

1. **从 `integration` 测试开始**: 对于一个已有代码的项目，先为你的 Repository（仓储库）编写集成测试，确保数据持久化层是可靠的。这能以最快速度获得最大回报。
2. **补全 `unit` 测试**: 接着，为核心的领域服务和复杂的业务逻辑函数编写单元测试。
3. **最后添加 `e2e` 测试**: 为最关键的几个 API 流程（例如，用户注册、创建核心资源）编写端到端测试，确保核心用户路径的正确性。
4. **利用 `conftest.py`**: 将所有测试共享的设置（如数据库连接、FastAPI `TestClient` 实例、数据工厂函数）都放在 `conftest.py` 中，以 Fixture 的形式提供给测试函数，保持测试代码的整洁。
5. **使用 Pytest Markers**: 为不同类型的测试打上标记（`@pytest.mark.unit`, `@pytest.mark.integration`），这样可以分类别运行测试，例如在本地开发时只运行快速的单元测试。

---

## 质量标准索引

关于具体的代码检查工具（flake8, mypy）、CI 流水线配置、Pre-commit 钩子及自动化修复脚本，请查阅单一事实来源文档：
👉 **[ci-standards.md](ci-standards.md)**

---
