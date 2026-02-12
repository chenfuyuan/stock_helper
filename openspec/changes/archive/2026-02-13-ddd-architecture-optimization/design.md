## Context

项目已有三个 Bounded Context（`data_engineering`、`llm_platform`、`research`），声明遵循 DDD + Clean Architecture，但审计中发现 **四大类问题**：

1. **依赖方向违规**：`research/presentation` 直接 import `data_engineering.infrastructure` 的仓储实现（`pg_quote_repo`、`pg_finance_repo`），以及 `main.py` 直接 import `llm_platform.infrastructure` 的 `PgLLMConfigRepository`、`LLMRegistry`。
2. **God Config**：`shared/config.py` 混合了所有模块的配置（Tushare 限速、同步批量、LLM API Key、Bocha API Key 等），违反模块隔离。
3. **DI 缺失**：依赖注入散落在各路由文件的 `Depends` 工厂函数中（每个路由文件 8-10 个工厂函数），跨路由有大量重复（如 `get_llm_service`、`get_llm_adapter` 在 3 个路由文件各写一遍）。
4. **文件命名/SRP 违规**：DTO 混入 `domain/ports/`；DTO 文件命名不一致（`dtos.py` vs `financial_dtos.py`）；UseCase 与 DTO 混写；`PlaceholderValue` 类型别名重复定义等 11 项问题。

**约束**：
- Python 3.10+、FastAPI、PostgreSQL（async SQLAlchemy）、APScheduler
- `dependency-injector` 已在 `environment.yml`（已安装但项目中未使用）
- 外部 HTTP 接口不能变（纯内部重构）
- 新模块 Coordinator / Debate / Judge 即将落地，需为其建立参考范式

## Goals / Non-Goals

**Goals:**

1. **修复依赖方向**：所有跨模块调用仅通过 Application 接口，Presentation 层不接触其他模块的 Infrastructure。
2. **引入 Composition Root**：统一的依赖组装入口，消除路由级工厂函数重复。
3. **配置模块化**：各 Bounded Context 拥有独立的配置类，`shared/config.py` 仅保留全局配置。
4. **文件组织规范化**：DTO 归入正确目录、文件名与类名对齐、消除命名不一致和 SRP 违规。
5. **为新模块建立参考范式**：完成后的目录结构和 DI 模式即为新模块的标准模板。

**Non-Goals:**

- 不引入新的外部 DI 框架（不使用 `dependency-injector` 库）——决策见 Decision 1。
- 不修改 Application 层 UseCase 的业务逻辑或签名。
- 不修改对外 HTTP API 的路径和响应结构。
- 不重构数据库 ORM Model 或 migration（纯代码组织重构）。
- 不在本次变更中创建新模块（Coordinator / Debate / Judge）。

## Decisions

### Decision 1: DI 方案——手写 Composition Root（不用 dependency-injector）

**选择**：在 `src/modules/<context>/container.py` 中手写工厂函数，每个模块一个 Container 类，统一管理本模块内部的依赖组装。

```python
# src/modules/research/container.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.research.application.technical_analyst_service import TechnicalAnalystService
from src.modules.research.infrastructure.adapters.market_quote_adapter import MarketQuoteAdapter
# ... 其他 import

class ResearchContainer:
    """Research 模块的 Composition Root，统一管理模块内部的依赖组装。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def technical_analyst_service(self) -> TechnicalAnalystService:
        """组装技术分析师服务的完整依赖链。"""
        market_quote_adapter = MarketQuoteAdapter(
            get_daily_bars_use_case=self._build_daily_bars_use_case()
        )
        indicator_calculator = IndicatorCalculatorAdapter()
        analyst_agent = TechnicalAnalystAgentAdapter(
            llm_port=self._build_llm_adapter()
        )
        return TechnicalAnalystService(
            market_quote_port=market_quote_adapter,
            indicator_calculator=indicator_calculator,
            analyst_agent_port=analyst_agent,
        )

    def _build_daily_bars_use_case(self) -> GetDailyBarsForTickerUseCase:
        from src.modules.data_engineering.application.queries.get_daily_bars_for_ticker import (
            GetDailyBarsForTickerUseCase,
        )
        from src.modules.data_engineering.container import DataEngineeringContainer
        de_container = DataEngineeringContainer(self._session)
        return de_container.get_daily_bars_use_case()

    def _build_llm_adapter(self) -> LLMAdapter:
        from src.modules.llm_platform.application.services.llm_service import LLMService
        return LLMAdapter(llm_service=LLMService())
```

**替代方案 A**：使用 `dependency-injector` 库。  
→ 已安装但未使用，引入后所有开发者需学习其 DSL（`providers.Factory`、`providers.Singleton` 等）。项目当前 3 个模块、6 个 Application Service，复杂度不足以证明框架的引入成本。

**替代方案 B**：保持现状（路由级 Depends 工厂）。  
→ 每增加一个 Agent 就需复制 8-10 个工厂函数到新路由文件；`get_llm_service`、`get_llm_adapter` 已在 3 个文件重复。新模块（Coordinator / Debate / Judge）会使重复问题不可控。

**理由**：手写 Container 是最轻量的方案。每个模块的 Container 类封装依赖组装逻辑，路由文件只需调用 `container.xxx_service()` 一行。与 FastAPI 的 `Depends` 是正交关系——路由通过 `Depends` 获取 session，传给 Container 即可。未来若复杂度增长再迁移到 `dependency-injector` 也很容易（Container 的 public API 不变）。

### Decision 2: 配置模块化——每模块一个 Config 类

**选择**：各 Bounded Context 在 `infrastructure/config.py` 中定义自己的 `BaseSettings` 子类，`shared/config.py` 瘦身为仅含全局配置。

```python
# src/shared/config.py（瘦身后）
class Settings(BaseSettings):
    PROJECT_NAME: str = "Stock Helper"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "local"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "stock_helper"
    POSTGRES_PORT: int = 5432
    # ...（DB 连接组装 validator 保留）
    class Config:
        case_sensitive = True
        env_file = ".env"

# src/modules/data_engineering/infrastructure/config.py
class DataEngineeringConfig(BaseSettings):
    TUSHARE_TOKEN: str = "your_tushare_token_here"
    TUSHARE_MIN_INTERVAL: float = 0.35
    SYNC_DAILY_HISTORY_BATCH_SIZE: int = 50
    SYNC_FINANCE_HISTORY_BATCH_SIZE: int = 100
    SYNC_FINANCE_HISTORY_START_DATE: str = "20200101"
    SYNC_INCREMENTAL_MISSING_LIMIT: int = 300
    SYNC_FAILURE_MAX_RETRIES: int = 3
    class Config:
        case_sensitive = True
        env_file = ".env"

de_config = DataEngineeringConfig()

# src/modules/llm_platform/infrastructure/config.py
class LLMPlatformConfig(BaseSettings):
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = "your_llm_api_key_here"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"
    BOCHA_API_KEY: str = ""
    BOCHA_BASE_URL: str = "https://api.bochaai.com"
    class Config:
        case_sensitive = True
        env_file = ".env"

llm_config = LLMPlatformConfig()
```

**替代方案**：保留单一 God Config，通过 `settings.TUSHARE_TOKEN` 方式访问。  
→ 新模块（Coordinator / Debate / Judge）加入后配置项将持续膨胀；模块间配置无物理隔离，任何模块都能访问无关配置。

**理由**：每个模块只能读自己的配置，物理性强制隔离。`.env` 文件不变（Pydantic `BaseSettings` 自动从同一个 `.env` 加载），迁移零风险。

### Decision 3: 跨模块依赖修复——仅通过 Application 接口

**选择**：`research/presentation` 的路由文件不再 import `data_engineering.infrastructure.persistence.repositories.*`，改为 import `data_engineering.application.queries.*` 的 UseCase。依赖组装（UseCase → Repo）在 `data_engineering/container.py` 内部完成。

**当前（违规）**：
```python
# research/presentation/rest/technical_analyst_routes.py
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import StockDailyRepositoryImpl
```

**目标**：
```python
# research/container.py
from src.modules.data_engineering.container import DataEngineeringContainer
# 通过 Container 获取 UseCase，不接触其 Infrastructure
```

**理由**：Presentation 层应仅依赖同模块的 Application 层和 Infrastructure Container；跨模块依赖通过对方模块的 Container 或 Application 接口获取。这完全符合 `tech-standards.md` 的跨模块调用规范。

### Decision 4: main.py 启动逻辑治理

**选择**：将 `main.py` 的 LLM Registry 初始化逻辑提取到 `llm_platform/application/services/` 中的启动服务方法，`main.py` 仅调用该方法。

```python
# main.py（重构后）
@app.on_event("startup")
async def startup_event():
    SchedulerService.start()
    await LLMPlatformStartup.initialize()  # Application 层服务

# src/modules/llm_platform/application/services/startup.py
class LLMPlatformStartup:
    @staticmethod
    async def initialize():
        """初始化 LLM 注册表，从数据库加载配置。"""
        async with AsyncSessionLocal() as session:
            container = LLMPlatformContainer(session)
            registry = container.llm_registry()
            await registry.refresh()
```

**理由**：`main.py` 应该是纯粹的组合入口（import 并调用），不应包含具体的 Infrastructure wiring 代码。

### Decision 5: 路由注册模块自治

**选择**：各模块在 `presentation/rest/__init__.py` 中导出统一的 `router`（合并模块内所有子路由），`src/api/routes.py` 仅 include 模块级 router。

```python
# src/modules/research/presentation/rest/__init__.py
from fastapi import APIRouter
from .technical_analyst_routes import router as technical_analyst_router
from .financial_auditor_routes import router as financial_auditor_router
from .valuation_modeler_routes import router as valuation_modeler_router

router = APIRouter(prefix="/research", tags=["Research"])
router.include_router(technical_analyst_router)
router.include_router(financial_auditor_router)
router.include_router(valuation_modeler_router)

# src/api/routes.py（简化后）
from src.modules.data_engineering.presentation.rest import router as de_router
from src.modules.llm_platform.presentation.rest import router as llm_router
from src.modules.research.presentation.rest import router as research_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(de_router)
api_router.include_router(llm_router)
api_router.include_router(research_router)
```

**理由**：新模块只需在 `routes.py` 加一行 `include_router`，无需知道模块内部有多少子路由。模块内的路由拆分/合并是模块自己的事。

### Decision 6: agents 目录迁移到 infrastructure

**选择**：`research/agents/` → `research/infrastructure/agents/`。

内容不变，仅调整目录位置和 import 路径。`agents/` 下的文件（Agent Adapter 实现）本质是 Infrastructure 层组件（加载 Prompt、调用 LLM、解析结果），应归入 `infrastructure/`。

**理由**：保持四层结构一致性。审查发现 `agents/` 已经被 Adapter 模式重构，实际文件位于 `infrastructure/adapters/` 下，`agents/` 目录下仅剩 Prompt 模板文件。若 `agents/` 仅含 Prompt 模板，则迁入 `infrastructure/agents/prompts/` 更合理。

### Decision 7: DTO 目录重组

**选择**：按 `tech-standards.md` 的模块内部结构规范，将 DTO 从 `domain/ports/` 迁出到 `domain/dtos/`：

```
research/domain/dtos/
├── __init__.py
├── daily_bar_input.py              # DailyBarInput（原 ports/dto_inputs.py）
├── financial_record_input.py       # FinanceRecordInput（原 ports/dto_financial_inputs.py 拆分）
├── financial_snapshot.py           # FinancialSnapshotDTO（原 ports/dto_financial_inputs.py 拆分）
├── valuation_inputs.py             # StockOverviewInput, ValuationDailyInput（原 ports/dto_valuation_inputs.py 拆分）
├── valuation_snapshot.py           # ValuationSnapshotDTO（原 ports/dto_valuation_inputs.py 拆分）
├── technical_analysis_dtos.py      # 原 domain/dtos.py 重命名
├── financial_dtos.py               # 保持不变
├── valuation_dtos.py               # 保持不变
├── indicators_snapshot.py          # 保持不变
└── types.py                        # PlaceholderValue（去重，统一定义）
```

**理由**：`domain/ports/` 仅放 Port 接口（ABC 抽象类），DTO 与 Port 分离。同时拆分混合 DTO 文件，确保一个文件一个职责。

### Decision 8: 文件名与类名统一

**选择**：将 `data_engineering/domain/model/daily_bar.py` 重命名为 `stock_daily.py`，与实体类名 `StockDaily` 对齐。

**理由**：遵循 `tech-standards.md` 的「文件名 = 主类名（snake_case）」规范。选择改文件名而非类名，因为 `StockDaily` 在多处被引用（import、ORM 映射），改类名影响面更大。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **大量 import 路径变更** | 一次性修改约 30+ 文件的 import 语句，可能遗漏 | 全局 `grep` 验证旧路径不再出现；CI 中 `python -c "import src.main"` 验证启动不报错 |
| **Container 类膨胀** | 随着 Agent 增加，Container 工厂方法增多 | 按职责拆分 private 方法；极端情况下可拆为多个子 Container |
| **config 迁移遗漏** | 某处仍引用 `settings.TUSHARE_TOKEN` 而非 `de_config.TUSHARE_TOKEN` | `grep` 扫描所有 `settings.` 引用，逐一确认是否为全局配置 |
| **Prompt 模板路径变化** | `agents/` 迁移后，Prompt 模板的 `Path` 引用需更新 | 统一使用 `__file__` 相对路径加载 Prompt，而非硬编码绝对路径 |
| **测试 import 路径失效** | 现有测试中 import 旧路径需要批量更新 | 与源码同步修改；CI 绿灯为验收标准 |

## Migration Plan

分三个阶段执行，每个阶段可独立提交和验证：

### Phase 1: 配置拆分 + Container 引入（无 import 路径变更）

1. 创建 `data_engineering/infrastructure/config.py` 和 `llm_platform/infrastructure/config.py`
2. 将模块配置项从 `shared/config.py` 移到对应模块的 config
3. 全局 `grep` 替换 `settings.TUSHARE_*` → `de_config.TUSHARE_*` 等
4. 创建各模块的 `container.py`
5. 提取 `main.py` 的 LLM 初始化逻辑到 `LLMPlatformStartup`
6. **验证**：`python -c "import src.main"` 正常启动

### Phase 2: 依赖方向修复 + 路由模块自治

1. 重构路由文件：移除手工工厂函数，改用 Container
2. 移除 `research/presentation` 中对 `data_engineering.infrastructure` 的直接 import
3. 各模块 `presentation/rest/__init__.py` 导出统一 router
4. 简化 `src/api/routes.py`
5. **验证**：所有 API 端点功能不变；`grep "data_engineering.infrastructure" research/` 返回空

### Phase 3: 文件命名与 SRP 治理

1. `research/domain/ports/dto_*.py` → `research/domain/dtos/`（迁移 + 拆分）
2. `research/domain/dtos.py` → `research/domain/dtos/technical_analysis_dtos.py`
3. `data_engineering/domain/model/daily_bar.py` → `stock_daily.py`
4. `data_engineering/application/commands/get_stock_basic_info.py` → `queries/`
5. `PlaceholderValue` 提取到 `research/domain/dtos/types.py`
6. `research/agents/` → `research/infrastructure/agents/`（若有残留内容）
7. 全局 import 路径更新 + `grep` 验证
8. **验证**：CI 全绿；`grep` 确认旧路径不再出现

## Open Questions

1. **`StockBasicInfoDTO` 是否需要立即扁平化？** 当前 `StockBasicInfoDTO.info: StockInfo` 直接引用领域实体。完全扁平化需要增加约 15 个字段。建议本次仅在 DTO 上添加 `# TODO: 扁平化字段，消除领域实体引用` 注释，在后续功能迭代中逐步替换引用方。
2. **`SyncTask` 是否从 `dataclass` 迁移到 Pydantic？** `tech-standards.md` 已规定统一使用 Pydantic。`SyncTask` 拥有行为方法（`start()`、`complete()` 等），迁移到 Pydantic 需确认 `model_config` 的 `frozen` 设置不影响这些方法的可变性。建议本次迁移，使用 `model_config = ConfigDict(from_attributes=True)` 且不设 `frozen`。
