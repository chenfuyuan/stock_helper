# 愿景与模块架构（Source of Truth）

**用途**：本文档是当前系统**能力与边界**的单一事实来源。做需求拆分、OpenSpec change、或实现新功能时，以本文档的 Bounded Context 划分与目录映射为准，禁止跨边界堆逻辑或绕过 Ports 直接依赖。

---

## 1. 核心愿景与架构哲学

本项目旨在构建**AI 原生（AI-Native）的虚拟投资团队**，核心哲学为 **「价值为盾，投机为矛」**。系统通过 **「采集 → 辩论 → 决策」** 的仿生流程，模拟顶尖投研团队的协作与对抗。

**架构哲学：**

- **异步优先**：情报采集与研究分析并行执行，避免串行阻塞。
- **证据驱动**：观点必须基于硬数据（DB）或软情报（搜索），杜绝 LLM 幻觉。
- **对抗决策**：通过多空辩论引入博弈，降低决策偏见。

采用 **Domain-Driven Design (DDD)**：每个模块为一个 **Bounded Context**，内部遵循 Presentation / Application / Domain / Infrastructure 四层，对外仅通过 **Ports** 暴露能力，依赖方通过 **Adapters** 接入。

---

## 2. 上下文映射（Context Map）

模块间**允许的依赖方向**（下游 → 上游，即下游依赖上游的 Ports）：

```
                    ┌─────────────────┐
                    │   Coordinator   │  编排层（唯一入口）
                    └────────┬────────┘
                              │ 编排
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Research    │  │      Debate     │  │      Judge       │
│  （仅消费下游）   │  │  （仅消费报告）   │  │  （仅消费辩论）   │
└────────┬────────┘  └─────────────────┘  └─────────────────┘
         │
         │ 通过 Ports 只读/只调
         ▼
┌───────────────────────┐     ┌───────────────────────┐
│   data_engineering    │     │     llm_platform      │
│   （硬数据：行情/财报）  │     │   （软情报：LLM 调用）  │
└───────────────────────┘     └───────────────────────┘
```

- **研究流水线**：Coordinator → Research → Debate → Judge（单向，无回流）。
- **支撑模块**：Research 可依赖 data_engineering、llm_platform 的 Ports；Coordinator / Debate / Judge 不直接依赖支撑模块（若需数据，经 Research 产出物传递）。

**模块间调用约定**：跨模块调用**必须**通过**被调用模块的 Application 接口**（应用服务/用例）进行；**禁止**跨模块直接依赖或使用对方模块的**内部领域模型**（实体、值对象、领域服务、Repository 实现等）。每个模块对外暴露的是 Application 层的“做什么”能力，入参/出参使用 DTO 或 Port 定义的抽象类型，调用方不接触对方 Domain/Infrastructure 的实现细节。

---

## 3. 模块划分与职责边界

### 3.1 研究部门核心模块（四个 Bounded Contexts）

| 模块 | 定位 | 边界（只做/不做） | 关键产出 |
|------|------|-------------------|----------|
| **Coordinator** | 前台与流程总管 | 只做：任务创建、流程编排、状态治理、结果汇总。不做：研究、多空观点、投资决策。 | `ResearchTask`、流程状态 |
| **Research** | 事实工厂 | 只做：并行五专家分析、证据采集（调 data_engineering / llm_platform）、报告生成。不做：辩论、决策、创建研究任务。 | `ResearchReport`（证据链 + 观点 + 置信度） |
| **Debate** | 观点熔炉与风控 | 只做：多空对抗、风险矩阵、冲突消解。不做：数据采集、研究、最终决策。 | `DebateOutcome`（多空观点 + 风险矩阵） |
| **Judge** | 最终裁决者 | 只做：综合裁决、操作指令与仓位建议、风控约束。不做：研报、辩论流程、回写研究结论。 | 买入/卖出/观望 + 止损止盈 |

**Research 五专家角色**：宏观情报员、财务审计员、估值建模师、催化剂侦探、技术分析师。

### 3.2 支撑模块（已实现）

| 模块 | 定位 | 边界（只做/不做） | 对外 Ports（示例） |
|------|------|-------------------|--------------------|
| **data_engineering** | 数据底座 | 只做：数据接入、转换、存储、按需查询、同步任务调度。不做：研报、辩论、决策。 | stock_basic_provider/repo, market_quote_provider/repo, financial_data_provider/repo |
| **llm_platform** | 大模型网关 | 只做：LLM 配置管理、多厂商路由、Chat/Completion。不做：研报、辩论、决策。 | config_repo, Chat/Completion 统一接口（经 adapters） |

---

## 4. 目录映射（实现时必遵）

新增或归属代码时，必须落在下表对应路径下，且不跨模块直接引用基础设施实现。

| Bounded Context | 代码路径 |
|-----------------|----------|
| Coordinator | `src/modules/coordinator/` |
| Research | `src/modules/research/` |
| Debate | `src/modules/debate/` |
| Judge | `src/modules/judge/` |
| data_engineering | `src/modules/data_engineering/` |
| llm_platform | `src/modules/llm_platform/` |
| 共享内核 | `src/shared/`（config、db、logging、公共 Port 定义等） |

各模块内部结构：`application/`、`domain/`（含 `ports/`）、`infrastructure/`、`presentation/`。

---

## 5. 设计/实现约束（检查清单）

- [ ] 新功能/变更已归属到上述某一 Bounded Context，且未跨边界堆逻辑。
- [ ] 模块间仅通过 **Ports** 通信；禁止跨模块直接依赖 infrastructure（如 repo 实现类、外部 API 客户端）。
- [ ] **模块间调用必须通过被调用模块的 Application 接口**；禁止跨模块直接使用对方模块的领域模型（实体、值对象、领域服务等）。
- [ ] 研究流水线方向固定：Coordinator 编排 → Research（可调 data_engineering、llm_platform）→ Debate → Judge；支撑模块仅作为被调用方。
- [ ] 目录与 `§4 目录映射` 一致；新模块命名与 `src/modules/<name>/` 一致。
