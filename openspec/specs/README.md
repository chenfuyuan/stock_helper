# OpenSpec 规格文档导航

> **本文档是 OpenSpec 规格目录的入口索引**。新加入项目的成员请按「推荐阅读顺序」逐步了解系统全貌，再按需深入各 spec。

---

## 1. 项目全景

**Stock Helper** 是一套 **AI 原生（AI-Native）的虚拟投资团队**系统。核心哲学：**「价值为盾，投机为矛」**。

系统模拟顶尖投研团队的协作与对抗，通过 **采集 → 辩论 → 决策** 的仿生流程生成结构化投资决策。

**技术栈**：Python 3.10+ · FastAPI · PostgreSQL · Alembic · LangGraph · Pydantic · DDD 四层架构

---

## 2. 端到端数据流

一次完整的研究请求经过以下阶段（单向，无回流）：

```
用户 POST /api/v1/coordinator/research
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  ① Coordinator（编排层）                                  │
│     校验入参 → 创建 ResearchSession → 启动 LangGraph 图    │
└────────────────────────┬────────────────────────────────┘
                         │ 按用户选择的专家 fan-out（并行）
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 技术分析师   │ │ 财务审计员   │ │ 估值建模师   │  ← Research 五专家
│ (硬数据)    │ │ (硬数据)    │ │ (硬+软数据) │     （任选 1~5 个）
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
┌──────┴──────┐ ┌──────┴──────┐       │
│ 宏观情报员   │ │ 催化剂侦探   │       │
│ (软情报:搜索)│ │ (软情报:搜索)│       │
└──────┬──────┘ └──────┬──────┘       │
       └───────────────┼───────────────┘
                       ▼
              ② 结果聚合（Aggregator）
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  ③ Debate（辩论层）                                       │
│     Bull Advocate ∥ Bear Advocate → Resolution Judge     │
│     输出：方向 / 置信度 / 多空论点 / 风险矩阵 / 冲突消解    │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  ④ Judge（裁决层）                                        │
│     综合裁决：BUY / SELL / HOLD + 仓位 + 止损止盈          │
└────────────────────────┬────────────────────────────────┘
                         ▼
              ⑤ 响应返回（含 session_id）
```

**支撑模块**（不直接参与流水线编排）：
- **data_engineering**：硬数据底座（股票列表、日线行情、财务指标）
- **llm_platform**：大模型网关 + Web 搜索网关（博查 AI）
- **knowledge_center**：知识图谱（股票知识图谱、概念板块信息）
- **market_insight**：市场洞察（市场情绪、舆情分析）

---

## 3. 推荐阅读顺序

| 步骤 | 文档 | 目的 |
|------|------|------|
| **1** | [vision-and-modules.md](vision-and-modules.md) | 理解模块边界、Context Map、目录映射 |
| **2** | [tech-standards.md](tech-standards.md) | 理解代码规范、分层规则、AI 响应协议 |
| **3** | 本文档 §4「Spec 分类索引」 | 按模块快速定位各能力的 spec |
| **4** | 按你负责的模块，深入阅读对应的 spec | 理解具体的需求、场景、DTO 契约 |

---

## 4. Spec 分类索引

### 4.1 核心流水线模块

#### Coordinator（编排层）— `src/modules/coordinator/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [coordinator/spec.md](coordinator/spec.md) | 研究编排核心：REST 端点、LangGraph 图、按需路由 5 专家、Debate/Judge 集成、流水线执行跟踪、执行上下文传播、研究任务重试 | ✅ 已实现 |

#### Research（研究层）— `src/modules/research/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [research/technical-analyst/spec.md](research/technical-analyst/spec.md) | 技术分析师：K 线指标 + LLM 定性分析 → 技术面信号 | ✅ 已实现 |
| [research/financial-auditor/spec.md](research/financial-auditor/spec.md) | 财务审计员：多期财务指标 + LLM → 5D 财务健康评分 | ✅ 已实现 |
| [research/valuation-modeler/spec.md](research/valuation-modeler/spec.md) | 估值建模师：分位点/PEG/Graham + LLM → 内在价值评估 | ✅ 已实现 |
| [research/macro-intelligence/spec.md](research/macro-intelligence/spec.md) | 宏观情报员：Web 搜索（4 维度宏观情报）+ LLM → 宏观环境评估 | ✅ 已实现 |
| [research/catalyst-detective/spec.md](research/catalyst-detective/spec.md) | 催化剂侦探：Web 搜索（4 维度催化事件）+ LLM → 催化剂评估 | ✅ 已实现 |
| [research/error-consistency/spec.md](research/error-consistency/spec.md) | 五专家异常类型/返回值类型/默认值统一 | ✅ 已实现 |
| [research/search-quality/spec.md](research/search-quality/spec.md) | 搜索查询构造规范 + 结果过滤 + 维度级参数差异化 | ✅ 已实现 |
| [research/narrative-reports/spec.md](research/narrative-reports/spec.md) | 9 个 Agent 同时产出结构化 JSON + 中文叙述性报告 | ✅ 已实现 |

#### Debate（辩论层）— `src/modules/debate/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [debate/spec.md](debate/spec.md) | 三阶段辩论：Bull ∥ Bear → Resolution → DebateOutcome | ✅ 已实现 |

#### Judge（裁决层）— `src/modules/judge/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [judge/spec.md](judge/spec.md) | 综合裁决：BUY/SELL/HOLD + 仓位 + 止损止盈 + 风控约束 | ✅ 已实现 |

### 4.2 支撑模块

#### data_engineering — `src/modules/data_engineering/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [data-engineering/spec.md](data-engineering/spec.md) | 统一数据同步：全量/增量/断点续跑/失败重试/配置外部化、DE  Clean Architecture 重构、AKShare 数据同步、财务数据合理性校验、数据适配器空值防护、技术指标数据量门槛、概念数据源、资金流分析 | ✅ 已实现 |

#### llm_platform — `src/modules/llm_platform/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [llm-platform/spec.md](llm-platform/spec.md) | Web 搜索网关、搜索结果 DB 缓存、LLM 调用审计日志、外部 API 调用日志、LLM JSON 重试、统一 LLM 输出解析器 | ✅ 已实现 |

#### foundation — `src/modules/foundation/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [foundation/spec.md](foundation/spec.md) | 调度器服务、调度配置持久化与执行记录、模块级依赖注入根、模块配置隔离、文件命名与单一职责清理 | ✅ 已实现 |

#### market_insight — `src/modules/market_insight/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [market-insight/spec.md](market-insight/spec.md) | 市场洞察核心能力、市场情绪指标 | ✅ 已实现 |

#### knowledge_center — `src/modules/knowledge_center/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [knowledge-center/spec.md](knowledge-center/spec.md) | 知识图谱 Schema 定义、知识图谱数据同步、知识图谱查询 | ✅ 已实现 |

---

## 5. Spec 命名约定

- **`<模块>/spec.md`**：模块级聚合 spec，包含该模块的所有 capabilities
- 每个模块 spec 内部按 capability 组织，使用 `---` 分隔不同 capability

---

## 6. 相关资源

| 资源 | 路径 | 说明 |
|------|------|------|
| OpenSpec 配置 | `openspec/config.yaml` | 项目上下文摘要，创建 change 时自动注入 |
| 已归档变更 | `openspec/changes/archive/` | 已完成并归档的 change |
| 进行中变更 | `openspec/changes/` | 当前正在进行的 change |
| OpenSpec SOP | `docs/openspec-sop.md` | 使用 OpenSpec 的标准操作流程 |
| 技术规范 | [tech-standards.md](tech-standards.md) | 代码风格、响应协议、测试约定 |
| 愿景与模块 | [vision-and-modules.md](vision-and-modules.md) | 模块边界（Source of Truth） |

