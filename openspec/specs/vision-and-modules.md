# 愿景与模块架构 (System Architecture & Vision)

> **Source of Truth**: 本文档是系统**能力边界**与**顶层架构**的单一事实来源。在进行需求拆分或架构决策时，必须严格遵循本文档定义的 Bounded Context（限界上下文）划分。

---

## 1. 核心愿景 (Executive Summary)

**项目目标**：构建一个 **AI 原生（AI-Native）的虚拟量化投研团队**。系统通过仿生流程模拟人类顶尖投资团队的协作、对抗与决策机制。

**核心哲学**：**「价值为盾，投机为矛」**
- **价值为盾 (Shield)**：基于财报、基本面数据的客观分析，确保本金安全。
- **投机为矛 (Spear)**：利用技术面、市场情绪捕捉超额收益机会。

**关键原则**：
1.  **证据驱动 (Evidence-Based)**：所有观点必须有明确的数据支撑（Database）或可信情报（Search），严控 LLM 幻觉。
2.  **对抗决策 (Adversarial Decision)**：引入多空辩论机制，通过观点博弈降低单一模型的偏见。
3.  **异步演进 (Asynchronous Evolution)**：各专家/模块并行工作，通过状态机编排协作。

---

## 2. 架构风格 (Architectural Style)

本系统采用 **模块化单体 (Modular Monolith)** 架构，结合 **领域驱动设计 (DDD)** 战术模式。

-   **严格封装**：每个模块也是一个 Bounded Context，物理上位于 `src/modules/<name>/`。
-   **洋葱架构**：模块内部遵循整洁架构分层（Presentation -> Application -> Domain -> Infrastructure）。
-   **依赖倒置**：模块对外仅暴露 **Ports (Interfaces)** 和 **Application Services**；模块间禁止直接引用内部 Domain Model。

---

## 3. 上下文映射 (Context Map)

系统由 **业务核心层** 和 **支撑能力层** 组成。箭头表示**依赖方向**（Use Dependency）。

```
[ 业务编排层 ]
      │
      ▼
┌───────────────┐
│  Coordinator  │ (任务总管：状态机、流程控制)
└──────┬────────┘
       │ 调度
       ▼
┌─────────────────────────────────────────────────────────┐
│                     业务核心层 (Core Domain)             │
│                                                         │
│   ┌────────────┐      ┌──────────┐      ┌───────────┐   │
│   │  Research  │ ───► │  Debate  │ ───► │   Judge   │   │
│   │ (事实工厂)  │      │ (观点熔炉) │      │ (最终裁决) │   │
│   └──────┬─────┘      └──────────┘      └───────────┘   │
└──────────┼──────────────────────────────────────────────┘
           │ 依赖 (通过 Ports)
           ▼
┌─────────────────────────────────────────────────────────┐
│                   支撑能力层 (Supporting Domain)         │
│                                                         │
│   ┌────────────────────┐      ┌─────────────────────┐   │
│   │  data_engineering  │◄────►│    llm_platform     │   │
│   │  (硬数据/ETL)       │      │   (AI 网关/路由)     │   │
│   └─────────┬──────────┘      └─────────────────────┘   │
│             │ 同步            ▲                        │
│             ▼                │ 提供数据                │
│   ┌────────────────────┐    │                         │
│   │  knowledge_center  │    │                         │
│   │  (知识中心)         │    │                         │
│   └────────────────────┘    │                         │
│                              │                         │
│   ┌────────────────────┐    │                         │
│   │  market_insight    │────┘                         │
│   │  (板块洞察)         │                              │
│   └─────────┬──────────┘                              │
│             │ 消费数据                                │
│             ▼                                        │
│   ┌────────────────────┐                              │
│   │  data_engineering  │◄─────────────────────────────┘
│   │  (硬数据/ETL)       │
│   └────────────────────┘
└─────────────────────────────────────────────────────────┘
```

**依赖规则**：
1.  **单向流动**：`Coordinator` -> `Research` -> `Debate` -> `Judge`。数据流向不可逆。
2.  **跨层调用**：业务层可调用支撑层；支撑层**严禁**反向依赖业务层。
3.  **支撑互通**：`data_engineering` 与 `llm_platform` 可通过共享内核或适配器有限互通（例如：数据清洗需调用 LLM）。

---

## 4. 模块注册表 (Module Registry)

新代码必须归属到以下标准模块中。

### 4.1 业务核心模块

| 模块 | 路径 (`src/modules/`) | 核心职责 (Bounded Context) | 关键产出 (Artifacts) |
| :--- | :--- | :--- | :--- |
| **Coordinator** | `coordinator/` | **流程编排**。负责任务生命周期管理、状态流转、异常恢复。不包含业务逻辑，只负责"谁在什么时候做什么"。 | Task, WorkflowState |
| **Research** | `research/` | **信息采集与分析**。扮演 5 类专家（宏观、财务、估值、催化剂、技术），生成客观研报。 | ResearchReport, SubReports |
| **Debate** | `debate/` | **多空博弈**。基于研报进行红蓝军对抗，识别风险点，生成辩论纪要。 | DebateTranscript, RiskMatrix |
| **Judge** | `judge/` | **投资决策**。综合研报与辩论结果，给出最终交易指令与仓位建议。 | TradingSignal, PositionSizing |

### 4.2 支撑与通用模块

| 模块 | 路径 | 核心职责 | 对外暴露接口 (Ports) |
| :--- | :--- | :--- | :--- |
| **Data Engineering** | `src/modules/data_engineering/` | **数据底座**。行情、财报数据的 ETL、存储与查询。 | `StockRepo`, `FinancialRepo` |
| **LLM Platform** | `src/modules/llm_platform/` | **AI 基础设施**。模型路由、Prompt 管理、计费统计。 | `LLMService`, `PromptManager` |
| **Market Insight** | `src/modules/market_insight/` | **板块洞察分析**。概念热度计算、涨停扫描归因、每日复盘报告生成。 | `GetConceptHeatQuery`, `GetLimitUpQuery`, `GenerateDailyReportCmd` |
| **Knowledge Center** | `src/modules/knowledge_center/` | **知识中心**。全系统知识资产管理、图谱构建与神经中枢推理。 | `GraphRepository`, `GraphService` |
| **Shared Kernel** | `src/shared/` | **共享内核**。全系统通用的值对象、异常定义、工具类、基础架构代码（日志、DB Session）。 | `AppException`, `Money`, `logger` |

---

## 5. 通信与协作模式 (Communication Patterns)

### 5.1 模块间通信 (Inter-Module)
-   **同步调用 (Method Call)**：优先使用。调用方通过 DI (Dependency Injection) 注入被调用方的 **Application Service Interface**。
    -   *Example*: `Research` 模块通过 `StockDataProvider` (Port) 调用 `DataEngineering` 的适配器实现。
-   **数据传输 (DTOs)**：跨模块交互**必须**使用 DTO (Data Transfer Object)，禁止传递 Entity 或 ORM Model。

### 5.2 共享内核 (Shared Kernel)
-   位于 `src/shared/`。
-   仅包含**高度通用**、**极少变更**的代码。
-   **严禁**将包含具体业务逻辑的代码放入 Shared，防止产生“上帝模块”。

---

## 6. 设计检查清单 (Design Checklist)

在提交设计或代码前，请自检：

-   [ ] **边界明确**：功能是否已归入正确的 Bounded Context？是否存在逻辑泄露？
-   [ ] **依赖合规**：是否遵守了 `Coordinator -> Core -> Supporting` 的依赖方向？
-   [ ] **接口隔离**：跨模块调用是否通过 `application/` 层的接口进行？是否避免了直接 import 对方 `domain/` 下的实体？
-   [ ] **数据解耦**：模块间传递的数据对象 (DTO) 是否与数据库模型解耦？

---

> **注意**：如需新增顶层模块或修改模块依赖关系，必须发起 RFC (Request For Comments) 并更新本文档。

