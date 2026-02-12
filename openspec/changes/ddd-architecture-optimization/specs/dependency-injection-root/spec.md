## ADDED Requirements

### Requirement: 模块级 Composition Root

每个 Bounded Context 须在 `<module>/container.py` 中定义一个 Container 类，作为该模块的统一依赖组装入口。Container 类封装所有 Infrastructure → Application 的 wiring 逻辑，Presentation 层通过 Container 获取 Application Service 实例，不再手写工厂函数链。

#### Scenario: Container 提供 Application Service

- **WHEN** Presentation 层路由需要某个 Application Service（如 `TechnicalAnalystService`）
- **THEN** 路由函数通过 `ResearchContainer(session).technical_analyst_service()` 一次调用获取完整装配的 Service 实例，无需在路由文件中定义多个 `Depends` 工厂函数

#### Scenario: Container 封装跨模块依赖

- **WHEN** Research 模块需要 data_engineering 的 `GetDailyBarsForTickerUseCase`
- **THEN** `ResearchContainer` 内部通过 `DataEngineeringContainer(session).get_daily_bars_use_case()` 获取，Research 的 Presentation 层不直接 import `data_engineering.infrastructure` 下的任何类

#### Scenario: Container 消除工厂函数重复

- **WHEN** 多个路由文件（如 `technical_analyst_routes.py`、`financial_auditor_routes.py`、`valuation_modeler_routes.py`）都需要 `LLMAdapter`
- **THEN** `LLMAdapter` 的构建逻辑仅在 Container 中定义一次，所有路由文件复用同一个 Container 方法

### Requirement: 路由文件精简

重构后的路由文件须仅包含：路由定义、请求/响应模型、从 Container 获取 Service 的一行 `Depends`。所有依赖组装逻辑须从路由文件移除。

#### Scenario: 路由文件无工厂函数

- **WHEN** 审查任意模块的 `presentation/rest/*.py` 路由文件
- **THEN** 文件中不存在手写的 `async def get_xxx_repo()` 或 `def get_xxx_adapter()` 工厂函数链，仅有一个获取 Container 或 Service 的 `Depends` 声明

### Requirement: main.py 不直接使用 Infrastructure

`main.py` 的 startup 逻辑须通过 Application 层服务完成初始化，不直接 import 或实例化 Infrastructure 层组件。

#### Scenario: main.py 启动 LLM Registry

- **WHEN** 应用启动执行 `startup_event()`
- **THEN** `main.py` 调用 `LLMPlatformStartup.initialize()`（Application 层方法），不直接 import `PgLLMConfigRepository` 或 `LLMRegistry`

### Requirement: 路由注册模块自治

各模块在 `presentation/rest/__init__.py` 中导出统一的 `router`，`src/api/routes.py` 仅做模块级 router 聚合。

#### Scenario: routes.py 仅包含模块级 include

- **WHEN** 审查 `src/api/routes.py`
- **THEN** 文件中每个模块仅有一行 `api_router.include_router(xxx_router)`，不直接引用模块内部的子路由文件（如 `technical_analyst_routes`、`config_routes` 等）

#### Scenario: 新增模块路由

- **WHEN** 新增一个 Bounded Context（如 `coordinator`）需要暴露 REST API
- **THEN** 只需在 `coordinator/presentation/rest/__init__.py` 导出 `router`，并在 `routes.py` 增加一行 `include_router`，无需修改其他模块
