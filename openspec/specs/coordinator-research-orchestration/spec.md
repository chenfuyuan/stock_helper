# Spec: coordinator-research-orchestration

Coordinator 模块的核心能力：通过单一 REST 端点接受研究请求（标的 + 用户指定的专家列表 + 可选参数），基于 LangGraph 有向图按需并行调用 Research 模块对应的专家 Application 服务，汇总各专家结果后统一返回。Coordinator 只做编排，不做研究、辩论或决策。

**五专家类型**：`technical_analyst`（技术分析师）、`financial_auditor`（财务审计员）、`valuation_modeler`（估值建模师）、`macro_intelligence`（宏观情报员）、`catalyst_detective`（催化剂侦探）。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: REST 端点 — POST /api/v1/coordinator/research

Coordinator 模块 SHALL 暴露 `POST /api/v1/coordinator/research` REST 端点，位于 `src/modules/coordinator/presentation/rest/` 下。该路由 SHALL 通过 FastAPI 依赖注入装配 `ResearchOrchestrationService` 所需的全部 Port 实现，并在路由函数中调用 `ResearchOrchestrationService.execute(request)`。路由 SHALL 在 `src/api/routes.py` 中注册。

路由 SHALL 处理以下异常并返回对应 HTTP 状态码：
- 入参校验失败（symbol 缺失、experts 为空或含非法类型）→ 400
- 全部专家执行失败 → 500
- 其他未预期异常 → 500（记录日志）

#### Scenario: HTTP 接口可正常调用

- **WHEN** 发送 `POST /api/v1/coordinator/research` 请求，请求体包含有效的 symbol 和至少一个合法的 expert
- **THEN** 系统 SHALL 通过依赖注入装配服务并返回研究编排结果，HTTP 状态码为 200

#### Scenario: symbol 缺失时返回 400

- **WHEN** 发送请求时 symbol 为空或缺失
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: experts 为空时返回 400

- **WHEN** 发送请求时 experts 列表为空数组
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: experts 含非法类型时返回 400

- **WHEN** 发送请求时 experts 列表包含不在 ExpertType 枚举中的值（如 `"unknown_expert"`）
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: 全部专家失败时返回 500

- **WHEN** 所有选定的专家均执行失败
- **THEN** 系统 SHALL 返回 HTTP 500，响应体包含错误信息

---

### Requirement: 请求体与响应体契约

REST 端点的请求体 SHALL 为 JSON，包含以下字段：
- `symbol`（str，必填）：股票代码
- `experts`（list[str]，必填）：需要执行的专家类型列表，值为 ExpertType 枚举的 value（snake_case），至少 1 个
- `options`（dict[str, dict]，可选）：按专家名提供的专家特有参数。`technical_analyst` 可接受 `analysis_date`（str，ISO 格式日期，默认当天）；`financial_auditor` 可接受 `limit`（int，默认 5）；其他三专家无额外参数。

响应体 SHALL 为 JSON，包含以下字段：
- `symbol`（str）：请求的股票代码
- `overall_status`（str）：`"completed"`（全部成功）、`"partial"`（部分成功部分失败）、`"failed"`（全部失败）
- `expert_results`（dict[str, object]）：按专家名分组的结果，每个专家的值包含 `status`（`"success"` 或 `"failed"`）、成功时包含 `data`（该专家的原始分析结果 dict）、失败时包含 `error`（错误信息字符串）

#### Scenario: 请求含完整字段时正确解析

- **WHEN** 发送请求体 `{"symbol": "000001.SZ", "experts": ["technical_analyst", "macro_intelligence"], "options": {"technical_analyst": {"analysis_date": "2026-02-13"}}}`
- **THEN** 系统 SHALL 正确解析 symbol、experts 列表和专家特有参数，调用对应的专家服务

#### Scenario: options 缺失时使用默认值

- **WHEN** 发送请求体不包含 `options` 字段，或 options 中不包含某专家的参数
- **THEN** 系统 SHALL 使用默认值（technical_analyst 默认 analysis_date 为当天，financial_auditor 默认 limit 为 5），正常执行

#### Scenario: 响应体包含 overall_status 和按专家分组的结果

- **WHEN** 研究编排执行完成（部分或全部成功）
- **THEN** 响应体 SHALL 包含 `symbol`、`overall_status`、`expert_results`，其中 `expert_results` 的 key 为专家名，value 包含 `status` 和 `data` 或 `error`

#### Scenario: 全部成功时 overall_status 为 completed

- **WHEN** 所有选定专家均执行成功
- **THEN** `overall_status` SHALL 为 `"completed"`，所有 expert_results 中的 status 均为 `"success"`

#### Scenario: 部分成功时 overall_status 为 partial

- **WHEN** 部分选定专家执行成功、部分失败
- **THEN** `overall_status` SHALL 为 `"partial"`，成功的专家 status 为 `"success"` 含 data，失败的专家 status 为 `"failed"` 含 error

---

### Requirement: 用户指定专家的按需路由

Coordinator SHALL 仅调用用户在 `experts` 列表中指定的专家，SHALL NOT 调用未被指定的专家。路由逻辑 SHALL 支持任意 1 至 5 个专家的组合。

#### Scenario: 仅调用指定的专家

- **WHEN** 用户指定 `experts: ["macro_intelligence", "catalyst_detective"]`
- **THEN** 系统 SHALL 仅调用宏观情报员和催化剂侦探，SHALL NOT 调用技术分析师、财务审计员、估值建模师

#### Scenario: 指定单个专家

- **WHEN** 用户指定 `experts: ["valuation_modeler"]`
- **THEN** 系统 SHALL 仅调用估值建模师，返回仅含该专家结果的响应

#### Scenario: 指定全部五个专家

- **WHEN** 用户指定全部五个专家类型
- **THEN** 系统 SHALL 调用全部五个专家，返回包含五个专家结果的响应

---

### Requirement: 选定专家并行执行

Coordinator SHALL 并行执行所有选定的专家（通过 LangGraph `Send` API 实现动态 fan-out）。各专家的执行 SHALL 互不阻塞，不存在顺序依赖。

#### Scenario: 多专家并行执行

- **WHEN** 用户指定 3 个专家
- **THEN** 系统 SHALL 并行调用这 3 个专家，而非顺序逐个调用；总耗时 SHALL 接近最慢专家的耗时而非各专家耗时之和

#### Scenario: 单专家无需并行

- **WHEN** 用户仅指定 1 个专家
- **THEN** 系统 SHALL 直接执行该专家，结果正常返回

---

### Requirement: 单专家失败隔离与优雅降级

单个专家执行失败（异常、超时等）SHALL NOT 导致整体编排中断或其他专家的结果丢失。系统 SHALL 按以下规则处理：
- 失败的专家：记录警告日志，在响应中标记 `status: "failed"` 并附带错误信息。
- 其他成功的专家：结果正常返回。
- `overall_status` 反映整体状态：全部成功 → `"completed"`、部分成功 → `"partial"`、全部失败 → `"failed"`。

#### Scenario: 一个专家失败不影响其他专家

- **WHEN** 用户指定 3 个专家，其中 1 个执行时抛出异常，其余 2 个正常返回
- **THEN** 系统 SHALL 返回 HTTP 200，`overall_status` 为 `"partial"`，失败的专家在 `expert_results` 中标记 `status: "failed"` 并附带 error，成功的 2 个专家正常返回 data

#### Scenario: 全部专家失败

- **WHEN** 用户指定的所有专家均执行失败
- **THEN** 系统 SHALL 返回错误响应，`overall_status` 为 `"failed"`，每个专家的 error 信息均被记录

---

### Requirement: 跨模块调用通过 Domain Port

Coordinator 调用 Research 模块的专家 SHALL 通过 Coordinator Domain 层定义的 `IResearchExpertGateway` Port 进行。该 Port 的 Infrastructure Adapter（`ResearchGatewayAdapter`）内部调用 Research 模块的 Application 服务接口。Coordinator 的 Application 层和 Domain 层 SHALL NOT 直接依赖 Research 模块的任何类型（服务类、DTO、Domain 实体等）。

#### Scenario: 通过 Gateway Port 调用专家

- **WHEN** Coordinator 需要调用某个 Research 专家
- **THEN** 通过注入的 `IResearchExpertGateway` Port 调用 `run_expert(expert_type, symbol, options)`，不直接实例化或引用 Research 模块的 Application Service 类

#### Scenario: Gateway Adapter 归一化催化剂侦探返回值

- **WHEN** Gateway Adapter 调用 `CatalystDetectiveService.run()` 获得 `CatalystDetectiveAgentResult`（非 dict）
- **THEN** Adapter SHALL 将其归一化为 `dict[str, Any]`，使 Coordinator 拿到的所有专家结果类型一致

---

### Requirement: LangGraph 作为 Infrastructure 实现

LangGraph 的 `StateGraph`、`Send`、`TypedDict` State 等 API SHALL 仅出现在 Coordinator 的 Infrastructure 层（`infrastructure/orchestration/`）。Application 层 SHALL 通过 Domain Port（`IResearchOrchestrationPort`）委托编排执行，SHALL NOT 直接导入或使用 LangGraph 的任何类型。

#### Scenario: Application 层不依赖 LangGraph

- **WHEN** 检查 `src/modules/coordinator/application/` 下所有 Python 文件的 import 语句
- **THEN** SHALL NOT 包含任何 `langgraph` 或 `langchain` 相关的 import

#### Scenario: Domain 层不依赖 LangGraph

- **WHEN** 检查 `src/modules/coordinator/domain/` 下所有 Python 文件的 import 语句
- **THEN** SHALL NOT 包含任何 `langgraph` 或 `langchain` 相关的 import

#### Scenario: LangGraph 图构建在 Infrastructure 层

- **WHEN** 检查 LangGraph `StateGraph` 的构建与编译代码
- **THEN** 该代码 SHALL 位于 `src/modules/coordinator/infrastructure/orchestration/` 下

---

### Requirement: 编排服务入参校验

`ResearchOrchestrationService`（Application 层）SHALL 在调用编排 Port 之前校验输入：
- `symbol` 为空或 None 时，SHALL 抛出校验异常。
- `experts` 为空列表时，SHALL 抛出校验异常。
- `experts` 中含有不在 `ExpertType` 枚举中的值时，SHALL 抛出校验异常。

校验异常 SHALL 提供可区分的错误信息，便于 Presentation 层映射为 HTTP 400。

#### Scenario: symbol 缺失时校验拒绝

- **WHEN** 调用 `ResearchOrchestrationService.execute()` 时 symbol 为空字符串或 None
- **THEN** 服务 SHALL 抛出校验异常，不调用编排 Port

#### Scenario: experts 为空时校验拒绝

- **WHEN** 调用服务时 experts 为空列表
- **THEN** 服务 SHALL 抛出校验异常，不调用编排 Port

#### Scenario: experts 含非法值时校验拒绝

- **WHEN** 调用服务时 experts 列表包含 `"unknown_expert"`
- **THEN** 服务 SHALL 抛出校验异常，不调用编排 Port

---

### Requirement: ExpertType 枚举与 Domain 模型

Coordinator Domain 层 SHALL 定义 `ExpertType` 枚举，包含五个值：`TECHNICAL_ANALYST`、`FINANCIAL_AUDITOR`、`VALUATION_MODELER`、`MACRO_INTELLIGENCE`、`CATALYST_DETECTIVE`。枚举的 value SHALL 为 snake_case 字符串（如 `"technical_analyst"`），与 REST 请求体中的 experts 列表值一一对应。

Coordinator Domain 层 SHALL 定义以下 DTO：
- `ResearchRequest`：`symbol: str, experts: list[ExpertType], options: dict[str, dict]`
- `ExpertResultItem`：`expert_type: ExpertType, status: Literal["success", "failed"], data: dict | None, error: str | None`
- `ResearchResult`：`symbol: str, overall_status: Literal["completed", "partial", "failed"], expert_results: list[ExpertResultItem]`

#### Scenario: ExpertType 枚举涵盖五专家

- **WHEN** 检查 `ExpertType` 枚举定义
- **THEN** SHALL 包含 `TECHNICAL_ANALYST`、`FINANCIAL_AUDITOR`、`VALUATION_MODELER`、`MACRO_INTELLIGENCE`、`CATALYST_DETECTIVE` 五个成员，value 分别为对应的 snake_case 字符串

#### Scenario: REST 请求中的专家字符串可映射为 ExpertType

- **WHEN** REST 请求体 experts 列表包含 `"technical_analyst"`
- **THEN** 系统 SHALL 将其映射为 `ExpertType.TECHNICAL_ANALYST`

---

### Requirement: Coordinator 模块四层结构

Coordinator 模块 SHALL 位于 `src/modules/coordinator/`，遵循标准 DDD 四层结构：
- `application/`：ResearchOrchestrationService、DTO（ResearchRequest、ResearchResult）
- `domain/`：ExpertType 枚举、Port 接口（IResearchOrchestrationPort、IResearchExpertGateway）、领域异常
- `infrastructure/`：ResearchGatewayAdapter（调用 Research）、LangGraph 图构建与编排器
- `presentation/rest/`：FastAPI 路由

模块 SHALL 有 `container.py` 作为 Composition Root，负责装配全部依赖。

#### Scenario: 模块目录结构符合四层

- **WHEN** 检查 `src/modules/coordinator/` 目录
- **THEN** SHALL 包含 `application/`、`domain/`、`infrastructure/`、`presentation/` 四个子目录和 `container.py`

#### Scenario: 路由在 api/routes.py 中注册

- **WHEN** 检查 `src/api/routes.py`
- **THEN** SHALL 包含 Coordinator 路由的注册（如 `api_router.include_router(coordinator_router)`）

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可先实现再补测，不强制测试先行。

测试 SHALL 可通过 mock `IResearchExpertGateway` 完成，无需真实 LLM 或数据库连接。

#### Scenario: 测试覆盖入参校验拒绝

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：传入缺失 symbol / 空 experts / 非法 expert 类型，断言调用被拒绝并返回可区分错误

#### Scenario: 测试覆盖按需路由

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Gateway，指定 2 个专家，断言仅这 2 个专家的 `run_expert` 被调用、其余 3 个未被调用

#### Scenario: 测试覆盖单专家失败降级

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Gateway 中某专家抛异常，断言 overall_status 为 `"partial"`、失败专家的 error 被记录、成功专家的 data 正常返回

#### Scenario: 测试覆盖全部专家失败

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Gateway 中全部专家抛异常，断言 overall_status 为 `"failed"`

#### Scenario: 测试覆盖 Gateway Adapter dispatch

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Research Application Service，验证 `ResearchGatewayAdapter` 根据 ExpertType 正确调度到对应的 Service 并传递参数
