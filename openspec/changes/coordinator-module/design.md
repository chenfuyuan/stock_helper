# Design: Coordinator 模块 — 基于 LangGraph 的研究编排

## Context

系统愿景中 Coordinator 是流水线的起点和唯一编排入口。当前 Research 模块的五个专家（技术分析师、财务审计员、估值建模师、宏观情报员、催化剂侦探）已全部实现，各自暴露独立的 Application 服务与 REST 端点。Coordinator 需要将这些散落的专家能力统一编排，让用户通过一次请求指定标的与所需专家，并行执行后汇总返回。

**已有专家接口签名**（Coordinator 需适配的 Application 层调用方式）：

| 专家 | 服务类 | 入参 | 出参 |
|------|--------|------|------|
| 技术分析师 | `TechnicalAnalystService.run` | `ticker: str, analysis_date: date` | `dict[str, Any]` |
| 财务审计员 | `FinancialAuditorService.run` | `symbol: str, limit: int = 5` | `dict[str, Any]` |
| 估值建模师 | `ValuationModelerService.run` | `symbol: str` | `dict[str, Any]` |
| 宏观情报员 | `MacroIntelligenceService.run` | `symbol: str` | `dict[str, Any]` |
| 催化剂侦探 | `CatalystDetectiveService.run` | `symbol: str` | `CatalystDetectiveAgentResult` |

**约束**：
- 模块间调用必须通过被调用模块的 **Application 接口**，不直接依赖对方 Domain/Infrastructure。
- Coordinator **只做**编排，不做研究、辩论、决策。
- LangGraph 作为 Infrastructure 层实现，Domain/Application 层不直接依赖 LangGraph API。

## Goals / Non-Goals

**Goals:**

- 新建 `src/modules/coordinator/` 模块（四层 DDD 结构），作为研究流水线的统一入口。
- 基于 LangGraph `StateGraph` 实现研究编排图：用户指定专家列表 → 条件路由 → 并行执行 → 结果汇总。
- 每个专家节点独立容错：单专家失败不中断整体流程，失败信息隔离记录。
- 通过 Port 抽象解耦 LangGraph（Infrastructure）与领域逻辑（Domain），可测试、可替换。
- 暴露 `POST /api/v1/coordinator/research` REST 端点。

**Non-Goals:**

- 不实现 Debate、Judge 模块（但图结构预留接入点）。
- 不实现任务持久化或异步轮询（当前为同步请求-响应，LangGraph checkpointer 预留扩展）。
- 不改变 Research 模块已有的接口契约。
- 不实现结果缓存或定时预计算。

## Decisions

### 1. LangGraph 图架构：条件路由 + 并行 Fan-out

- **选择**：使用 LangGraph `StateGraph` 构建研究编排图。图包含 5 个专家节点（每专家一个），通过 `Send` API 从起始节点动态 fan-out 到用户选定的专家节点，实现**按需并行执行**。专家节点全部完成后汇入聚合节点，聚合节点组装最终结果。

  ```
  START → router (conditional edges via Send)
        → [technical_analyst_node]  ─┐
        → [financial_auditor_node]  ─┤
        → [valuation_modeler_node]  ─┼→ aggregator_node → END
        → [macro_intelligence_node] ─┤
        → [catalyst_detective_node] ─┘
  ```

  `router` 不是一个图节点，而是 `add_conditional_edges(START, route_to_experts)` 中的路由函数，它读取 `state["selected_experts"]` 并为每个选中的专家返回一个 `Send(expert_node_name, state)`。LangGraph 自动并行执行多个 Send 目标。

- **备选**：所有专家放在一个节点中用 `asyncio.gather` 手动并行。
- **理由**：LangGraph 的 `Send` 机制天然支持动态并行 fan-out，比手写 `asyncio.gather` + 错误收集更干净。每个专家作为独立图节点，状态更新自动合并（通过 `Annotated` reducer），天然隔离错误。且后续 Debate/Judge 可直接作为 `aggregator_node` 的下游节点接入，无需重构。

### 2. 图状态设计：TypedDict + Annotated Reducer

- **选择**：图状态使用 `TypedDict` + `Annotated` reducer 定义：

  ```python
  from typing import TypedDict, Annotated
  import operator

  class ResearchGraphState(TypedDict):
      symbol: str
      selected_experts: list[str]
      options: dict[str, dict]                            # 各专家的可选参数
      results: Annotated[dict[str, Any], merge_dicts]     # 专家名 → 结果
      errors: Annotated[dict[str, str], merge_dicts]      # 专家名 → 错误信息
  ```

  其中 `merge_dicts` 是自定义 reducer（合并两个 dict），使得并行节点各自写入自己的 key 后自动合并到同一 `results` / `errors` dict。

- **理由**：`Annotated` reducer 是 LangGraph 处理并行节点状态更新的标准方式，比全局锁或手动合并更安全。TypedDict 提供静态类型检查。

### 3. 跨模块调用：IResearchExpertGateway Port + Adapter

- **选择**：在 Coordinator 的 Domain 层定义 `IResearchExpertGateway`（ABC），提供一个通用方法：

  ```python
  class IResearchExpertGateway(ABC):
      @abstractmethod
      async def run_expert(
          self,
          expert_type: ExpertType,
          symbol: str,
          options: dict[str, Any] | None = None,
      ) -> dict[str, Any]:
          """调用指定类型的 Research 专家，返回该专家的分析结果。"""
  ```

  Infrastructure 层 `ResearchGatewayAdapter` 实现该 Port，内部通过 `ResearchContainer` 获取对应的 Application Service 并调用：

  ```python
  class ResearchGatewayAdapter(IResearchExpertGateway):
      def __init__(self, research_container: ResearchContainer):
          self._research = research_container

      async def run_expert(self, expert_type, symbol, options=None):
          options = options or {}
          match expert_type:
              case ExpertType.TECHNICAL_ANALYST:
                  svc = self._research.technical_analyst_service()
                  return await svc.run(
                      ticker=symbol,
                      analysis_date=options.get("analysis_date", date.today()),
                  )
              case ExpertType.FINANCIAL_AUDITOR:
                  svc = self._research.financial_auditor_service()
                  return await svc.run(symbol=symbol, limit=options.get("limit", 5))
              case ExpertType.VALUATION_MODELER:
                  svc = self._research.valuation_modeler_service()
                  return await svc.run(symbol=symbol)
              case ExpertType.MACRO_INTELLIGENCE:
                  svc = self._research.macro_intelligence_service()
                  return await svc.run(symbol=symbol)
              case ExpertType.CATALYST_DETECTIVE:
                  svc = self._research.catalyst_detective_service()
                  agent_result = await svc.run(symbol=symbol)
                  return self._normalize_catalyst_result(agent_result)
  ```

  `CatalystDetectiveService.run()` 返回 `CatalystDetectiveAgentResult` 而非 `dict`，Adapter 中做归一化处理，使 Coordinator 拿到的所有专家结果均为 `dict[str, Any]`。

- **备选 A**：为每个专家定义独立的 Gateway Port（5 个 ABC）。
- **备选 B**：Coordinator Infrastructure 直接 import Research 的 Application Service 类，不经 Port。
- **理由**：单一 Gateway + `match` 调度最简洁——5 个专家的差异仅在入参，返回类型统一为 dict 后消费方无差别。Port 抽象使 Application 和 LangGraph 节点不依赖 Research 模块的任何类型；测试时 mock 一个 Gateway 即可覆盖全部跨模块调用。备选 B 虽然更简单，但违反依赖倒置，且无法在不引入 Research 依赖的情况下单独测试 Coordinator。

### 4. LangGraph 节点实现：通用节点工厂

- **选择**：使用节点工厂函数，为每个专家类型生成对应的图节点函数：

  ```python
  def create_expert_node(
      expert_type: ExpertType,
      gateway: IResearchExpertGateway,
  ) -> Callable:
      async def expert_node(state: ResearchGraphState) -> dict:
          try:
              result = await gateway.run_expert(
                  expert_type=expert_type,
                  symbol=state["symbol"],
                  options=state["options"].get(expert_type.value, {}),
              )
              return {"results": {expert_type.value: result}}
          except Exception as e:
              logger.warning(f"专家 {expert_type.value} 执行失败: {e}")
              return {"errors": {expert_type.value: str(e)}}
      expert_node.__name__ = f"{expert_type.value}_node"
      return expert_node
  ```

  每个节点：从 state 读取 symbol + 自身 options → 调用 Gateway → 成功写入 `results`，失败写入 `errors`。异常被捕获，不会导致图执行中断。

- **理由**：工厂模式避免 5 份重复的节点代码，DRY 且一致。错误隔离在节点级别，符合 proposal 中「单专家失败不中断」的要求。

### 5. 聚合节点与结果校验

- **选择**：`aggregator_node` 检查 `state["results"]` 和 `state["errors"]`：
  - 若 `results` 为空（全部专家失败）→ 在 state 中标记 `overall_status = "failed"`。
  - 若 `results` 非空 → 标记 `overall_status = "completed"`（可能有部分 errors）。
  - 聚合结果不做二次加工，保持各专家原始输出结构。

  Application 层拿到图执行结果后，根据 `overall_status` 决定是返回成功响应还是抛出异常。

- **理由**：聚合逻辑保持简单——Coordinator 只汇总不加工。各专家的原始结果结构已包含 `input`、`output`、`*_indicators` 等审计字段，透传即可。

### 6. Application 层：薄编排 + Port 委托

- **选择**：`ResearchOrchestrationService`（Application 层）职责极薄：
  1. 校验输入（symbol 非空、experts 列表非空且合法）。
  2. 构建 `ResearchGraphState` 初始状态。
  3. 调用 `IResearchOrchestrationPort.run(initial_state)` → 获取最终 state。
  4. 根据最终 state 的 `overall_status` 返回成功 DTO 或抛出领域异常。

  `IResearchOrchestrationPort` 是 Domain 层定义的编排 Port：

  ```python
  class IResearchOrchestrationPort(ABC):
      @abstractmethod
      async def run(self, request: ResearchRequest) -> ResearchResult:
          """执行研究编排，返回汇总结果。"""
  ```

  Infrastructure 层 `LangGraphResearchOrchestrator` 实现该 Port，负责图的构建、编译与执行。

- **理由**：Application 不感知 LangGraph；Port 抽象使得编排实现可替换（如切换为简单的 `asyncio.gather` 实现做对比测试）。薄 Application 符合「编排层只做调度，不做业务逻辑」的原则。

### 7. Domain 模型

- **选择**：Coordinator Domain 层定义以下类型：
  - **`ExpertType`（枚举）**：`TECHNICAL_ANALYST | FINANCIAL_AUDITOR | VALUATION_MODELER | MACRO_INTELLIGENCE | CATALYST_DETECTIVE`。值为 snake_case 字符串（如 `"technical_analyst"`），与 REST 请求体中的 experts 列表值对应。
  - **`ResearchRequest`（Pydantic DTO）**：`symbol: str, experts: list[ExpertType], options: dict[str, dict]`。
  - **`ExpertResultItem`（Pydantic DTO）**：`expert_type: ExpertType, status: Literal["success", "failed"], result: dict | None, error: str | None`。
  - **`ResearchResult`（Pydantic DTO）**：`symbol: str, overall_status: Literal["completed", "partial", "failed"], expert_results: list[ExpertResultItem]`。其中 `partial` 表示部分专家成功、部分失败。

- **理由**：ResearchRequest/ResearchResult 作为 Port 的入参/出参 DTO，Application 和 Presentation 层消费这些 DTO 而非图状态的 TypedDict（隔离 LangGraph 实现细节）。ExpertType 枚举统一约束合法专家类型。

### 8. REST 端点设计

- **选择**：`POST /api/v1/coordinator/research`

  **请求体**：
  ```json
  {
    "symbol": "000001.SZ",
    "experts": ["technical_analyst", "macro_intelligence", "catalyst_detective"],
    "options": {
      "technical_analyst": { "analysis_date": "2026-02-13" }
    }
  }
  ```
  - `symbol`：必填。
  - `experts`：必填，至少 1 个，值为 ExpertType 枚举的 value。
  - `options`：可选，按专家名提供专家特有参数。技术分析师需要 `analysis_date`（默认当天）；财务审计员可传 `limit`（默认 5）；其他三专家无额外参数。

  **响应体**：
  ```json
  {
    "symbol": "000001.SZ",
    "overall_status": "completed",
    "expert_results": {
      "technical_analyst": { "status": "success", "data": { ... } },
      "macro_intelligence": { "status": "success", "data": { ... } },
      "catalyst_detective": { "status": "failed", "error": "..." }
    }
  }
  ```

  **HTTP 状态码**：
  - 200：至少一个专家成功（含 partial）。
  - 400：symbol 缺失、experts 为空或含非法类型。
  - 500：全部专家失败或系统异常。

- **理由**：POST 因为请求体含结构化 JSON；`experts` 列表式设计使调用方按需选择，无需预定义组合。响应按专家名分组，调用方可精确提取所需专家结果。

### 9. CoordinatorContainer（Composition Root）

- **选择**：`src/modules/coordinator/container.py` 定义 `CoordinatorContainer`，负责装配全部依赖：

  ```python
  class CoordinatorContainer:
      def __init__(self, session: AsyncSession):
          self._session = session

      def research_orchestration_service(self) -> ResearchOrchestrationService:
          research_container = ResearchContainer(self._session)
          gateway = ResearchGatewayAdapter(research_container)
          orchestrator = LangGraphResearchOrchestrator(gateway)
          return ResearchOrchestrationService(orchestrator)
  ```

  Presentation 层的 FastAPI `Depends` 中构造 `CoordinatorContainer`，获取 Service 实例。

- **理由**：与已有模块（ResearchContainer、DataEngineeringContainer、LLMPlatformContainer）一致的组合根模式。

### 10. 目录结构

```
src/modules/coordinator/
├── __init__.py
├── container.py                          # Composition Root
├── application/
│   ├── __init__.py
│   ├── research_orchestration_service.py # 薄编排服务
│   └── dtos/
│       ├── __init__.py
│       └── research_dtos.py              # ResearchRequest, ResearchResult, ExpertResultItem
├── domain/
│   ├── __init__.py
│   ├── model/
│   │   ├── __init__.py
│   │   └── enums.py                      # ExpertType 枚举
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── research_orchestration.py     # IResearchOrchestrationPort
│   │   └── research_expert_gateway.py    # IResearchExpertGateway
│   └── exceptions.py                     # Coordinator 领域异常
├── infrastructure/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── research_gateway_adapter.py   # ResearchGatewayAdapter (calls ResearchContainer)
│   └── orchestration/
│       ├── __init__.py
│       ├── graph_state.py                # ResearchGraphState (TypedDict)
│       ├── graph_builder.py              # LangGraph StateGraph 构建与编译
│       └── langgraph_orchestrator.py     # LangGraphResearchOrchestrator (implements Port)
└── presentation/
    ├── __init__.py
    └── rest/
        ├── __init__.py
        └── research_routes.py            # POST /coordinator/research
```

### 11. 实现顺序与测试

- **选择**：按层自底向上实现：Domain（枚举 + DTO + Port 接口）→ Infrastructure（Gateway Adapter + LangGraph 图）→ Application（Service）→ Presentation（REST）→ Container → 路由注册 → 测试。最后统一补测，确保所有 Spec Scenario 有对应通过测试。
- **测试策略**：
  - **单元测试**：mock `IResearchExpertGateway`，验证图路由逻辑（仅选中的专家被调用）、错误隔离（部分失败时结果正确聚合）、入参校验。
  - **集成测试**：mock Research 的各 Application Service，验证 `ResearchGatewayAdapter` 的 dispatch 逻辑。
  - 无需真实 LLM/DB 即可完整验证 Coordinator 逻辑。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| **引入 LangGraph 新依赖**：增加依赖复杂度，团队需学习 LangGraph API | LangGraph 封装在 Coordinator 的 Infrastructure 层，其他模块不感知；API 表面积小（StateGraph + Send + Annotated reducer）；后续 Debate→Judge 复用同一框架，学习成本分摊。 |
| **`langgraph` 间接依赖 `langchain-core`**：可能与已有 `openai` 包产生版本冲突 | LangGraph 0.3+ 的 `langchain-core` 依赖较轻；在 `requirements.txt` 中固定版本；容器环境中验证兼容性。 |
| **CatalystDetectiveService 返回类型不统一**（DTO 而非 dict）| Gateway Adapter 中做归一化，将 `CatalystDetectiveAgentResult` 转为 dict；Coordinator 层面不感知差异。 |
| **图并行执行的错误传播**：LangGraph 并行节点异常处理行为 | 每个节点内部 try/except 全覆盖，异常写入 state.errors 而非向上抛出；aggregator 负责判定整体状态。 |
| **同步请求-响应模式下的延迟**：5 个专家并行仍可能较慢（宏观/催化剂需 Web 搜索） | 用户按需选专家，减少无谓调用；HTTP 超时配置合理；后续可引入 LangGraph checkpointer + 异步轮询模式。 |
| **技术分析师 analysis_date 默认值**：用户不传时默认当天，但当天可能无交易数据 | 默认 `date.today()`，若当天无数据由 Research 层返回明确错误（已有逻辑），Coordinator 不做特殊处理。 |
