# Coordinator 模块 LangGraph 编排机制详解

## 1. 概述

Coordinator 模块是系统的研究编排中枢，负责接受研究请求并按需调用专家模块（Research、Debate、Judge），但不直接执行研究、辩论或决策。模块基于 **LangGraph** 构建有向图，实现专家节点的**动态并行执行**、**失败隔离**与**优雅降级**。

### 1.1 核心职责

- 接受研究请求（标的 + 用户指定的专家列表 + 可选参数）
- 基于 LangGraph 有向图按需并行调用 Research 模块的专家服务
- 汇总各专家结果，执行辩论与裁决阶段（可选）
- 管理研究会话生命周期与执行跟踪
- 支持任务重试机制

### 1.2 五专家类型

| 专家类型 | 枚举值 | 描述 |
|---------|--------|------|
| `TECHNICAL_ANALYST` | `technical_analyst` | 技术分析师 |
| `FINANCIAL_AUDITOR` | `financial_auditor` | 财务审计员 |
| `VALUATION_MODELER` | `valuation_modeler` | 估值建模师 |
| `MACRO_INTELLIGENCE` | `macro_intelligence` | 宏观情报员 |
| `CATALYST_DETECTIVE` | `catalyst_detective` | 催化剂侦探 |

---

## 2. 架构分层

Coordinator 模块遵循 DDD 四层架构，LangGraph 相关实现仅出现在 **Infrastructure 层**。

```
src/modules/coordinator/
├── application/
│   ├── research_orchestration_service.py  # 编排服务（入参校验、委托 Port）
│   └── dtos/
├── domain/
│   ├── ports/
│   │   ├── IResearchOrchestrationPort.py  # 编排 Port（抽象接口）
│   │   ├── IResearchExpertGateway.py      # 专家调用 Port
│   │   ├── IDebateGateway.py              # 辩论调用 Port
│   │   └── IJudgeGateway.py               # 裁决调用 Port
│   ├── model/
│   │   ├── enums.py                       # ExpertType 枚举
│   │   ├── research_session.py            # ResearchSession 实体
│   │   └── node_execution.py              # NodeExecution 实体
│   └── dtos/
│       └── research_dtos.py               # ResearchRequest/Result DTO
├── infrastructure/
│   ├── orchestration/
│   │   ├── langgraph_orchestrator.py      # LangGraphResearchOrchestrator 实现
│   │   ├── graph_builder.py               # 构建 LangGraph 图
│   │   ├── graph_state.py                 # ResearchGraphState 定义
│   │   ├── node_persistence_wrapper.py    # 节点执行持久化包装
│   │   └── reducers.py                    # 状态合并函数
│   ├── adapters/
│   │   ├── research_gateway_adapter.py    # 实现 IResearchExpertGateway
│   │   ├── debate_gateway_adapter.py      # 实现 IDebateGateway
│   │   └── judge_gateway_adapter.py       # 实现 IJudgeGateway
│   └── persistence/
│       └── research_session_repository.py # 会话仓储实现
└── presentation/rest/
    ├── research_routes.py                 # POST /research
    └── session_routes.py                  # GET /sessions
```

### 2.1 依赖规则

- **Application 层**：通过 `IResearchOrchestrationPort` 委托编排执行，**不直接导入 LangGraph**
- **Domain 层**：定义 Port 接口与 DTO，**不依赖 LangGraph**
- **Infrastructure 层**：LangGraph 的 `StateGraph`、`Send`、`TypedDict` 等 API **仅出现在此层**

---

## 3. LangGraph 编排核心组件

### 3.1 ResearchGraphState（图状态）

位置：`src/modules/coordinator/infrastructure/orchestration/graph_state.py`

使用 `TypedDict + Annotated reducer` 定义图状态，支持并行节点自动合并结果。

```python
class ResearchGraphState(TypedDict, total=False):
    """研究编排图状态。"""
    
    symbol: str
    selected_experts: list[str]
    options: dict[str, dict[str, Any]]
    results: Annotated[dict[str, Any], merge_dicts]
    errors: Annotated[dict[str, str], merge_dicts]
    overall_status: Literal["completed", "partial", "failed"]
    debate_outcome: dict[str, Any]  # 由 debate_node 写入
    verdict: dict[str, Any]  # 由 judge_node 写入
```

**关键字段说明**：

- `symbol`、`selected_experts`、`options`：输入参数
- `results`、`errors`：由各专家节点并行写入，通过 `merge_dicts` 自动合并
- `overall_status`：由聚合节点设置
- `debate_outcome`：辩论结果（可选）
- `verdict`：裁决结果（可选）

### 3.2 merge_dicts（状态 Reducer）

位置：`src/modules/coordinator/infrastructure/orchestration/reducers.py`

```python
def merge_dicts(left: dict, right: dict) -> dict:
    """合并两个 dict，右值覆盖左值同 key。
    
    用于 Annotated[dict, merge_dicts]，使并行专家节点写入的 {expert_name: result} 自动合并。
    """
    return {**left, **right}
```

**作用**：LangGraph 并行执行多个专家节点时，各节点返回的 `{"results": {expert_type: result}}` 会自动合并到全局 `results` 字段。

---

### 3.3 专家节点工厂

位置：`src/modules/coordinator/infrastructure/orchestration/graph_builder.py`

```python
def create_expert_node(
    expert_type: ExpertType,
    gateway: IResearchExpertGateway,
) -> Callable[[ResearchGraphState], dict[str, Any]]:
    """专家节点工厂：为指定专家类型生成图节点函数。"""
    node_name = EXPERT_NODE_NAMES[expert_type]
    
    async def expert_node(state: ResearchGraphState) -> dict[str, Any]:
        options = state.get("options") or {}
        expert_opts = options.get(expert_type.value, {})
        result = await gateway.run_expert(
            expert_type=expert_type,
            symbol=state["symbol"],
            options=expert_opts,
        )
        return {"results": {expert_type.value: result}}
    
    expert_node.__name__ = node_name
    return expert_node
```

**节点行为**：

1. 从图状态读取 `symbol` 和专家专属 `options`
2. 通过 `IResearchExpertGateway.run_expert()` 调用对应专家服务
3. 成功时返回 `{"results": {expert_type.value: result}}`
4. **失败时抛出异常**，停止整个编排流程

---

### 3.4 路由函数（动态 Fan-out）

```python
def route_to_experts(state: ResearchGraphState) -> list[Send]:
    """路由函数：读取 selected_experts，为每个选中的专家返回 Send(node_name, state)。
    
    用于 add_conditional_edges(START, route_to_experts)，实现按需并行 fan-out。
    """
    selected = state.get("selected_experts") or []
    sends: list[Send] = []
    for expert_value in selected:
        expert_type = ExpertType(expert_value)
        node_name = EXPERT_NODE_NAMES[expert_type]
        sends.append(Send(node_name, state))
    return sends
```

**关键机制**：

- 使用 LangGraph 的 `Send` API 实现**动态 fan-out**
- 仅调用用户在 `experts` 列表中指定的专家
- 支持任意 1 至 5 个专家的组合

---

### 3.5 聚合节点

```python
def create_aggregator_node() -> Callable[[ResearchGraphState], dict[str, Any]]:
    """聚合节点：根据 results 设置 overall_status。"""
    
    def aggregator_node(state: ResearchGraphState) -> dict[str, Any]:
        results = state.get("results") or {}
        overall_status = "completed" if results else "failed"
        return {"overall_status": overall_status}
    
    return aggregator_node
```

**职责**：

- 检查 `results` 是否为空
- 设置 `overall_status`（`completed` / `failed`）
- **专家失败时流程已停止**，无需处理 errors

---

### 3.6 辩论节点

```python
def create_debate_node(
    debate_gateway: Any,
) -> Callable[[ResearchGraphState], dict[str, Any]]:
    """debate 节点工厂：读取 results/overall_status，全部失败时跳过辩论。"""
    
    async def debate_node(state: ResearchGraphState) -> dict[str, Any]:
        overall_status = state.get("overall_status") or "failed"
        results = state.get("results") or {}
        symbol = state.get("symbol") or ""
        
        if overall_status == "failed" or not results:
            return {"debate_outcome": {}}
        
        try:
            outcome = await debate_gateway.run_debate(
                symbol=symbol, 
                expert_results=results
            )
            return {"debate_outcome": outcome}
        except Exception as e:
            logger.warning("辩论节点执行失败，降级为空结果：%s", e)
            return {"debate_outcome": {}}
    
    debate_node.__name__ = "debate_node"
    return debate_node
```

**降级策略**：

- 全部专家失败时**跳过辩论**
- 辩论异常时**记录日志并降级**，`debate_outcome` 设为空 dict
- **不影响** `overall_status` 和 `expert_results`

---

### 3.7 裁决节点

```python
def create_judge_node(
    judge_gateway: Any,
) -> Callable[[ResearchGraphState], dict[str, Any]]:
    """judge 节点工厂：读取 debate_outcome，为空时跳过裁决。"""
    
    async def judge_node(state: ResearchGraphState) -> dict[str, Any]:
        debate_outcome = state.get("debate_outcome") or {}
        symbol = state.get("symbol") or ""
        
        if not debate_outcome:
            return {"verdict": {}}
        
        try:
            verdict = await judge_gateway.run_verdict(
                symbol=symbol, 
                debate_outcome=debate_outcome
            )
            return {"verdict": verdict}
        except Exception as e:
            logger.warning("裁决节点执行失败，降级为空结果：%s", e)
            return {"verdict": {}}
    
    judge_node.__name__ = "judge_node"
    return judge_node
```

**降级策略**：

- 辩论被跳过或失败时**跳过裁决**
- 裁决异常时**记录日志并降级**，`verdict` 设为空 dict
- **不影响** `overall_status` 和 `debate_outcome`

---

## 4. 图构建流程

位置：`src/modules/coordinator/infrastructure/orchestration/graph_builder.py`

### 4.1 build_research_graph 函数

```python
def build_research_graph(
    gateway: IResearchExpertGateway,
    debate_gateway: Any = None,
    judge_gateway: Any = None,
    session_repo: IResearchSessionRepository | None = None,
) -> Any:
    """构建并编译研究编排图。"""
    builder = StateGraph(ResearchGraphState)
    
    def _wrap_if_persist(fn: Callable, node_type: str) -> Callable:
        if session_repo is not None:
            return persist_node_execution(fn, node_type, session_repo)
        return fn
    
    # 1. 注册 5 个专家节点
    for expert_type in ExpertType:
        node_name = EXPERT_NODE_NAMES[expert_type]
        node_fn = create_expert_node(expert_type, gateway)
        node_fn = _wrap_if_persist(node_fn, expert_type.value)
        builder.add_node(node_name, node_fn)
    
    # 2. 聚合节点
    builder.add_node("aggregator_node", create_aggregator_node())
    
    # 3. 根据 gateway 参数动态构建边
    if debate_gateway is not None:
        debate_fn = create_debate_node(debate_gateway)
        debate_fn = _wrap_if_persist(debate_fn, "debate")
        builder.add_node("debate_node", debate_fn)
        builder.add_edge("aggregator_node", "debate_node")
        
        if judge_gateway is not None:
            judge_fn = create_judge_node(judge_gateway)
            judge_fn = _wrap_if_persist(judge_fn, "judge")
            builder.add_node("judge_node", judge_fn)
            builder.add_edge("debate_node", "judge_node")
            builder.add_edge("judge_node", END)
        else:
            builder.add_edge("debate_node", END)
    else:
        builder.add_edge("aggregator_node", END)
    
    # 4. START -> 路由函数（动态 fan-out）
    builder.add_conditional_edges(START, route_to_experts)
    
    # 5. 各专家节点 -> 聚合节点
    for node_name in EXPERT_NODE_NAMES.values():
        builder.add_edge(node_name, "aggregator_node")
    
    return builder.compile()
```

### 4.2 图结构示例

**场景 1：完整流程（5 专家 + 辩论 + 裁决）**

```
START → route_to_experts → [technical_analyst_node, financial_auditor_node, ...] (并行)
                            ↓
                            aggregator_node
                            ↓
                            debate_node
                            ↓
                            judge_node
                            ↓
                            END
```

**场景 2：跳过辩论（skip_debate=true）**

```
START → route_to_experts → [专家节点并行] → aggregator_node → END
```

**场景 3：仅调用单个专家**

```
START → route_to_experts → [technical_analyst_node] → aggregator_node → END
```

---

## 5. 编排器实现

位置：`src/modules/coordinator/infrastructure/orchestration/langgraph_orchestrator.py`

### 5.1 LangGraphResearchOrchestrator 类

```python
class LangGraphResearchOrchestrator(IResearchOrchestrationPort):
    """基于 LangGraph 的研究编排器。"""
    
    def __init__(
        self,
        gateway: IResearchExpertGateway,
        debate_gateway: Any = None,
        judge_gateway: Any = None,
        session_repo: IResearchSessionRepository | None = None,
    ) -> None:
        self._gateway = gateway
        self._debate_gateway = debate_gateway
        self._judge_gateway = judge_gateway
        self._session_repo = session_repo
    
    async def run(self, request: ResearchRequest) -> ResearchResult:
        """执行研究编排，返回汇总结果。"""
        started_at = datetime.utcnow()
        session: ResearchSession | None = None
        token = None
        
        # 1. 创建 ResearchSession（如果启用持久化）
        if self._session_repo is not None:
            session = ResearchSession(...)
            await self._session_repo.save_session(session)
            token = current_execution_ctx.set(ExecutionContext(session_id=str(session.id)))
        
        try:
            # 2. 根据 skip_debate 决定是否传入辩论/裁决 gateway
            debate_gw = None if request.skip_debate else self._debate_gateway
            judge_gw = None if request.skip_debate else self._judge_gateway
            
            # 3. 构建图
            graph = build_research_graph(
                self._gateway,
                debate_gateway=debate_gw,
                judge_gateway=judge_gw,
                session_repo=self._session_repo,
            )
            
            # 4. 设置初始状态
            initial_state = {
                "symbol": request.symbol,
                "selected_experts": [e.value for e in request.experts],
                "options": request.options,
                "results": request.pre_populated_results or {},
            }
            
            # 5. 执行图
            final_state = await graph.ainvoke(initial_state)
            
            # 6. 从 final_state 提取结果
            results = final_state.get("results") or {}
            overall_status = final_state.get("overall_status") or "failed"
            
            # 7. 构建专家结果列表（含重试时复用的结果）
            expert_results: list[ExpertResultItem] = [...]
            
            # 8. 更新 session 状态
            if session and self._session_repo is not None:
                if overall_status == "completed":
                    session.complete(completed_at, duration_ms)
                else:
                    session.fail(completed_at, duration_ms)
                await self._session_repo.update_session(session)
            
            # 9. 返回 ResearchResult
            return ResearchResult(...)
            
        except Exception:
            # 10. 异常时会话置为失败
            if session is not None and self._session_repo is not None:
                session.fail(completed_at, duration_ms)
                await self._session_repo.update_session(session)
            raise
        finally:
            # 11. 重置执行上下文
            if token is not None:
                current_execution_ctx.reset(token)
```

### 5.2 执行流程

1. **创建会话**：生成 `ResearchSession`（UUID），状态设为 `running`
2. **设置上下文**：通过 `ContextVar` 设置 `ExecutionContext(session_id)`
3. **构建图**：根据 `skip_debate` 和 gateway 参数动态构建图结构
4. **注入初始状态**：包含 `symbol`、`selected_experts`、`options`、`pre_populated_results`（重试时）
5. **执行图**：`await graph.ainvoke(initial_state)`
6. **提取结果**：从 `final_state` 读取 `results`、`overall_status`、`debate_outcome`、`verdict`
7. **构建响应**：组装 `ResearchResult` DTO
8. **更新会话**：根据 `overall_status` 更新 `ResearchSession` 状态
9. **重置上下文**：在 `finally` 块中清理 `ExecutionContext`

---

## 6. 节点执行持久化

位置：`src/modules/coordinator/infrastructure/orchestration/node_persistence_wrapper.py`

### 6.1 persist_node_execution 包装器

```python
def persist_node_execution(
    node_fn: Callable[[ResearchGraphState], Any],
    node_type: str,
    session_repo: IResearchSessionRepository,
) -> Callable[[ResearchGraphState], Any]:
    """包装节点函数：记录 started_at → 执行 → 成功/失败记录 → 写入 NodeExecution。"""
    
    async def wrapper(state: ResearchGraphState) -> dict[str, Any]:
        ctx = current_execution_ctx.get()
        if not ctx:
            return await node_fn(state)
        
        session_id = UUID(ctx.session_id)
        started_at = datetime.utcnow()
        execution = NodeExecution(
            id=uuid4(),
            session_id=session_id,
            node_type=node_type,
            status="success",
            started_at=started_at,
        )
        try:
            result = await node_fn(state)
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # 提取 result_data 与 narrative_report
            result_data, narrative_report = _extract_result_and_narrative(node_type, result)
            
            # 清理 NaN/Inf，避免 PostgreSQL JSONB 写入失败
            sanitized_result_data = _sanitize_jsonb(result_data) if result_data else None
            
            execution.mark_success(
                result_data=sanitized_result_data or {},
                narrative_report=narrative_report,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
            try:
                await session_repo.save_node_execution(execution)
            except Exception as e:
                logger.warning("节点执行记录写入失败，不阻塞主流程：%s", e)
            return result
        except Exception as e:
            # 失败时记录 error
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            execution.mark_failed(
                error_type=type(e).__name__,
                error_message=str(e),
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
            try:
                await session_repo.save_node_execution(execution)
            except Exception as save_err:
                logger.warning("节点失败记录写入失败，不阻塞主流程：%s", save_err)
            raise
    
    wrapper.__name__ = getattr(node_fn, "__name__", f"persisted_{node_type}")
    return wrapper
```

### 6.2 包装策略

- **专家节点**、**debate 节点**、**judge 节点**均会被包装（如果提供 `session_repo`）
- 写入失败**不阻塞主流程**，仅记录 warning 日志
- 成功时记录 `result_data` 和 `narrative_report`
- 失败时记录 `error_type` 和 `error_message`

### 6.3 数据清理

```python
def _sanitize_jsonb(obj: Any) -> Any:
    """递归清理 Python 对象中的 NaN/Inf，将其转为 None，避免 PostgreSQL JSONB 写入失败。"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_jsonb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_jsonb(item) for item in obj]
    else:
        return obj
```

---

## 7. 跨模块调用（Gateway Adapter）

### 7.1 ResearchGatewayAdapter

位置：`src/modules/coordinator/infrastructure/adapters/research_gateway_adapter.py`

**职责**：

- 实现 `IResearchExpertGateway` 接口
- 通过 `ResearchContainer` 调用 Research 模块的 Application Service
- 每次 `run_expert` 使用**独立 AsyncSession**，避免 LangGraph 并行节点共享会话导致错误

```python
async def run_expert(
    self,
    expert_type: ExpertType,
    symbol: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """根据专家类型调度到对应的 Research Application Service。"""
    opts = options or {}
    
    async with self._session_factory() as session:
        research = ResearchContainer(session)
        match expert_type:
            case ExpertType.TECHNICAL_ANALYST:
                # 调用 technical_analyst_service
            case ExpertType.FINANCIAL_AUDITOR:
                # 调用 financial_auditor_service
            # ... 其他专家
```

---

### 7.2 DebateGatewayAdapter

**职责**：

- 实现 `IDebateGateway` 接口
- 通过 `DebateContainer` 调用 Debate 模块的 `DebateService`
- 将 `expert_results`（dict）转换为 `DebateInput` DTO
- 将 `DebateOutcomeDTO` 转换为 `dict[str, Any]` 返回

**DTO 转换规则**（5 专家字段归一化为 `ExpertSummary`）：

| 专家 | signal 来源 | confidence 来源 | reasoning 来源 | risk_warning 来源 |
|------|------------|----------------|---------------|------------------|
| technical_analyst | `signal` | `confidence` | `summary_reasoning` | `risk_warning` |
| financial_auditor | `signal` | `confidence` | `summary_reasoning` | `risk_warning` |
| valuation_modeler | `valuation_verdict` | `confidence_score` | `reasoning_summary` | `risk_factors` |
| macro_intelligence | `macro_environment` | `confidence_score` | `macro_summary` | `key_risks` |
| catalyst_detective | `result.catalyst_assessment` | `result.confidence_score` | `result.catalyst_summary` | `result.negative_catalysts` |

**过滤字段**（不传递给 Debate）：

- `input` / `user_prompt`：提示词原文
- `output` / `raw_llm_output`：LLM 原始输出
- `technical_indicators` / `financial_indicators`：原始指标数据
- `dimension_analyses`：详细分析数组（体积大）

---

### 7.3 JudgeGatewayAdapter

**职责**：

- 实现 `IJudgeGateway` 接口
- 通过 `JudgeContainer` 调用 Judge 模块的 `JudgeService`
- 将 `debate_outcome`（dict）转换为 `JudgeInput` DTO
- 将 `VerdictDTO` 转换为 `dict[str, Any]` 返回

**DTO 转换规则**（debate_outcome → JudgeInput）：

| JudgeInput 字段 | debate_outcome 来源 |
|----------------|-------------------|
| `symbol` | 由调用方传入的 `symbol` 参数 |
| `direction` | `debate_outcome["direction"]` |
| `confidence` | `debate_outcome["confidence"]` |
| `bull_thesis` | `debate_outcome["bull_case"]["core_thesis"]` |
| `bear_thesis` | `debate_outcome["bear_case"]["core_thesis"]` |
| `risk_factors` | `debate_outcome["risk_matrix"]` 中每项的 `risk` 字段 |
| `key_disagreements` | `debate_outcome["key_disagreements"]` |
| `conflict_resolution` | `debate_outcome["conflict_resolution"]` |

**过滤字段**（不传递给 Judge）：

- `bull_case.supporting_arguments`：多头论据列表
- `bear_case.acknowledged_risks`：空头风险列表
- `risk_matrix` 中每项的 `probability`、`impact`、`mitigation` 明细

---

## 8. 应用服务层

位置：`src/modules/coordinator/application/research_orchestration_service.py`

### 8.1 ResearchOrchestrationService

```python
class ResearchOrchestrationService:
    """研究编排应用服务。"""
    
    def __init__(
        self,
        orchestration_port: IResearchOrchestrationPort,
        session_repo: IResearchSessionRepository | None = None,
    ) -> None:
        self._orchestration_port = orchestration_port
        self._session_repo = session_repo
    
    async def execute(
        self,
        symbol: str,
        experts: list[str],
        options: dict[str, dict] | None = None,
        skip_debate: bool = False,
    ) -> ResearchResult:
        """执行研究编排。"""
        # 1. 校验 symbol
        if not symbol or not str(symbol).strip():
            raise BadRequestException(message="symbol 为必填")
        
        # 2. 校验 experts 非空且合法
        if not experts:
            raise BadRequestException(message="experts 为必填")
        
        valid_values = {e.value for e in ExpertType}
        expert_types: list[ExpertType] = []
        for ex in experts:
            if ex not in valid_values:
                raise BadRequestException(message=f"experts 含非法值：{ex}")
            expert_types.append(ExpertType(ex))
        
        # 3. 构建 ResearchRequest 并调用 Port
        request = ResearchRequest(
            symbol=symbol.strip(),
            experts=expert_types,
            options=options or {},
            skip_debate=skip_debate,
        )
        result = await self._orchestration_port.run(request)
        
        # 4. 全部失败时抛出领域异常
        if result.overall_status == "failed":
            raise AllExpertsFailedError(message="全部专家执行失败")
        
        return result
    
    async def retry(
        self,
        session_id: UUID,
        skip_debate: bool = False,
    ) -> ResearchResult:
        """对已有 session 中失败的专家发起重试。"""
        # 1. 查询源 session
        source_session = await self._session_repo.get_session_by_id(session_id)
        
        # 2. 校验状态
        if source_session.status == "completed":
            raise SessionNotRetryableError(message="该研究会话已完成，无需重试")
        if source_session.status == "running":
            raise SessionNotRetryableError(message="该研究会话正在执行中")
        
        # 3. 查询 NodeExecution，分离成功/失败专家
        node_executions = await self._session_repo.get_node_executions_by_session(session_id)
        success_results: dict[str, Any] = {}
        failed_experts: list[ExpertType] = []
        
        for ne in node_executions:
            if ne.node_type not in expert_values:
                continue
            if ne.status == "success" and ne.result_data is not None:
                success_results[ne.node_type] = ne.result_data
            elif ne.status == "failed":
                failed_experts.append(ExpertType(ne.node_type))
        
        # 4. 构建重试请求（仅失败专家 + 复用成功结果）
        request = ResearchRequest(
            symbol=source_session.symbol,
            experts=failed_experts,
            options=source_session.options or {},
            skip_debate=skip_debate,
            pre_populated_results=success_results if success_results else None,
            parent_session_id=session_id,
            retry_count=source_session.retry_count + 1,
        )
        
        # 5. 委托编排执行
        result = await self._orchestration_port.run(request)
        
        return result
```

---

## 9. 重试机制

### 9.1 重试流程

1. 用户调用 `POST /api/v1/coordinator/research/{session_id}/retry`
2. 查询源 `session`，校验状态（非 completed、非 running）
3. 查询该 `session` 的所有 `NodeExecution` 记录
4. 分离**成功专家**（status=success）和**失败专家**（status=failed）
5. 构建新的 `ResearchRequest`：
   - `experts` = 失败专家列表
   - `pre_populated_results` = 成功专家结果
   - `parent_session_id` = 源 session ID
   - `retry_count` = 源 session retry_count + 1
6. 委托编排器执行（复用结果的专家**不重新执行**）
7. 重新执行聚合/辩论/裁决阶段

### 9.2 图状态注入

```python
# LangGraphResearchOrchestrator.run()
initial_state = {
    "symbol": request.symbol,
    "selected_experts": [e.value for e in request.experts],  # 仅失败专家
    "options": request.options,
    "results": request.pre_populated_results or {},  # 复用成功结果
}

final_state = await graph.ainvoke(initial_state)
```

**效果**：

- 聚合节点读取 `results` 时，已包含复用的成功专家结果
- 仅执行未在 `pre_populated_results` 中的专家
- 辩论和裁决阶段**重新执行**（基于完整结果）

---

## 10. 执行上下文传播

位置：`src/shared/infrastructure/execution_context.py`

### 10.1 ExecutionContext 定义

```python
class ExecutionContext(BaseModel):
    """执行上下文，含 session_id。"""
    session_id: str

current_execution_ctx: ContextVar[ExecutionContext | None] = ContextVar(
    "current_execution_ctx", 
    default=None
)
```

### 10.2 上下文生命周期

```python
# LangGraphResearchOrchestrator.run()
token = None
try:
    if self._session_repo is not None:
        session = ResearchSession(...)
        await self._session_repo.save_session(session)
        token = current_execution_ctx.set(ExecutionContext(session_id=str(session.id)))
    
    # 执行图...
    
finally:
    if token is not None:
        current_execution_ctx.reset(token)
```

### 10.3 下游模块消费

下游模块（Research / Debate / Judge / llm_platform）通过 `current_execution_ctx.get()` **隐式获取**上下文：

```python
# LLMService.generate()
ctx = current_execution_ctx.get()
session_id = ctx.session_id if ctx else None

# 写入 LLMCallLog
llm_call_log = LLMCallLog(
    session_id=session_id,  # 无上下文时为 None
    ...
)
```

**特性**：

- 无上下文时**优雅降级**（session_id=null），不抛异常
- LangGraph 并行节点**共享同一 session_id**
- `finally` 块确保上下文**总是重置**

---

## 11. REST API

### 11.1 发起研究

**端点**：`POST /api/v1/coordinator/research`

**请求体**：

```json
{
  "symbol": "000001.SZ",
  "experts": ["technical_analyst", "macro_intelligence"],
  "options": {
    "technical_analyst": {
      "analysis_date": "2026-02-13"
    }
  },
  "skip_debate": false
}
```

**响应体**：

```json
{
  "symbol": "000001.SZ",
  "overall_status": "completed",
  "expert_results": [
    {
      "expert_type": "technical_analyst",
      "status": "success",
      "data": {...},
      "error": null
    },
    {
      "expert_type": "macro_intelligence",
      "status": "success",
      "data": {...},
      "error": null
    }
  ],
  "debate_outcome": {...},
  "verdict": {...},
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "retry_count": 0
}
```

---

### 11.2 重试研究

**端点**：`POST /api/v1/coordinator/research/{session_id}/retry`

**请求体**：

```json
{
  "skip_debate": false
}
```

**响应体**：

```json
{
  "symbol": "000001.SZ",
  "overall_status": "completed",
  "expert_results": [...],
  "debate_outcome": {...},
  "verdict": {...},
  "session_id": "新子 session ID",
  "retry_count": 1
}
```

---

### 11.3 查询历史会话

**端点**：`GET /api/v1/coordinator/research/sessions`

**查询参数**：

- `symbol`：股票代码（可选）
- `start_date` / `end_date`：时间范围（可选）
- `page` / `page_size`：分页（可选）

**响应**：会话列表（按 `created_at` 降序）

---

### 11.4 会话详情

**端点**：`GET /api/v1/coordinator/research/sessions/{session_id}`

**响应**：

- 会话基本信息（symbol、status、created_at、duration_ms、retry_count 等）
- 所有 `NodeExecution` 列表（按 `started_at` 排序）
  - node_type、status、result_data、narrative_report、error_type、error_message、duration_ms

---

## 12. 关键设计决策

### 12.1 为什么使用 LangGraph？

1. **动态 fan-out**：通过 `Send` API 实现按需并行调用专家
2. **状态管理**：`TypedDict + Annotated reducer` 自动合并并行节点结果
3. **可观测性**：图结构清晰，便于调试和监控
4. **失败隔离**：单节点失败可捕获降级，不影响其他节点

### 12.2 为什么 LangGraph 仅在 Infrastructure 层？

- **依赖倒置**：Application 层通过 Port 接口委托编排，不依赖具体实现
- **可替换性**：未来可替换为其他编排框架（如 Prefect、Airflow）
- **可测性**：Application 层测试可 mock Port，无需启动 LangGraph

### 12.3 为什么专家节点失败时抛异常？

- **快速失败**：避免部分专家失败后继续执行下游（辩论/裁决）
- **状态一致**：`overall_status` 反映真实情况（`partial` / `failed`）
- **重试机制**：失败专家记录到 `NodeExecution`，支持后续重试

### 12.4 为什么辩论/裁决节点失败时降级？

- **优雅降级**：研究和辩论结果仍可用，不整体失败
- **价值保留**：即使裁决失败，用户仍可获得专家分析和辩论结论
- **日志记录**：失败原因记录到 `NodeExecution`，便于排查

### 12.5 为什么每次 run_expert 使用独立 AsyncSession？

- **并发安全**：LangGraph 并行节点同时调用 `run_expert`
- **避免冲突**：SQLAlchemy AsyncSession 不支持并发操作
- **会话隔离**：各专家互不干扰

---

## 13. 总结

Coordinator 模块通过 LangGraph 实现了灵活、健壮的研究编排系统：

1. **按需并行**：用户指定专家列表，系统动态 fan-out 并行执行
2. **失败隔离**：单专家失败不影响其他专家，支持后续重试
3. **优雅降级**：辩论/裁决失败不整体失败，保留有价值结果
4. **执行跟踪**：持久化 ResearchSession 和 NodeExecution，支持历史查询
5. **上下文传播**：通过 ContextVar 隐式传递 session_id，下游模块无侵入
6. **重试机制**：仅重试失败专家，复用成功结果，节省成本

整个系统遵循 DDD 原则，LangGraph 作为 Infrastructure 实现细节，对 Application 层透明，保证了高内聚、低耦合的架构质量。
