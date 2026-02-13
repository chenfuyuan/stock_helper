# Spec: execution-context-propagation

执行上下文传播：在 shared 层定义 ExecutionContext（含 session_id）及 ContextVar，由 Coordinator 在研究流水线入口设置、出口重置；下游模块通过隐式获取上下文实现 LLM/API 调用与 session 的关联，且无上下文时优雅降级。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: ExecutionContext 定义

系统 SHALL 在 shared infrastructure 中定义 `ExecutionContext` 类型（Pydantic BaseModel），包含 `session_id: str` 字段，以及对应的 `ContextVar`（默认值为 None）。

#### Scenario: ExecutionContext 类型可用

- **WHEN** 任何模块 import `current_execution_ctx` 并调用 `.get()`
- **THEN** 在无上下文时返回 None，在有上下文时返回包含 session_id 的 ExecutionContext 实例

### Requirement: Coordinator 设置执行上下文

Coordinator 的编排入口 SHALL 在创建 `ResearchSession` 后、启动 LangGraph 流水线前，设置 `ExecutionContext`。流水线结束后（无论成功或失败）MUST 重置上下文。

#### Scenario: 正常流水线

- **WHEN** Coordinator 启动一次研究流水线
- **THEN** 在 `graph.ainvoke()` 执行前 `current_execution_ctx.get()` 返回包含正确 session_id 的 ExecutionContext，流水线执行期间所有下游调用均可获取该上下文

#### Scenario: 流水线异常退出

- **WHEN** 研究流水线执行过程中抛出未捕获异常
- **THEN** ExecutionContext 仍被正确重置（通过 try/finally），不影响后续请求

### Requirement: 下游模块隐式消费

下游模块（Research / Debate / Judge / llm_platform）的 Port 签名 SHALL NOT 包含 session_id 或 ExecutionContext 参数。日志记录层通过 `current_execution_ctx.get()` 隐式获取上下文。

#### Scenario: LLM 调用自动关联 session

- **WHEN** Research 模块的 Agent 在研究流水线中调用 `ILLMPort.generate(prompt, system_message, temperature)`（签名不含 session_id）
- **THEN** `LLMService` 内部通过 `current_execution_ctx.get()` 获取 session_id，写入 `LLMCallLog`

#### Scenario: Port 签名不变

- **WHEN** 审查 Research / Debate / Judge 模块的 `ILLMPort` 和 `IWebSearchProvider` 接口定义
- **THEN** 接口签名与变更前完全一致，不含 session_id 或 ExecutionContext 参数

### Requirement: 并行节点上下文隔离

LangGraph 并行执行多个专家节点时，各节点 SHALL 共享同一个 `session_id`（来自父上下文），且互不干扰。

#### Scenario: 5 个专家并行执行

- **WHEN** LangGraph 并行启动 5 个专家节点
- **THEN** 每个节点内调用 `current_execution_ctx.get()` 均返回相同的 session_id，且节点间的操作不会覆盖彼此的上下文

### Requirement: 无上下文时优雅降级

当 `current_execution_ctx.get()` 返回 None 时（非研究流水线调用），日志记录层 SHALL 正常工作，仅将 session_id 字段置为 null，不抛出异常。

#### Scenario: 独立 LLM 调用

- **WHEN** 在非研究流水线的上下文中（如直接调用 LLM API）调用 `LLMService.generate()`
- **THEN** `LLMCallLog` 正常创建，session_id 为 null，不抛出任何异常
