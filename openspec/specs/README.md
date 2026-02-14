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
| [coordinator-research-orchestration](coordinator-research-orchestration/spec.md) | 研究编排核心：REST 端点、LangGraph 图、按需路由 5 专家、Debate/Judge 集成 | ✅ 已实现 |
| [pipeline-execution-tracking](pipeline-execution-tracking/spec.md) | ResearchSession + NodeExecution 生命周期管理与历史查询 API | ✅ 已实现 |
| [execution-context-propagation](execution-context-propagation/spec.md) | ExecutionContext（session_id）隐式传播，下游模块自动关联 | ✅ 已实现 |
| [research-task-retry](research-task-retry/spec.md) | 对 partial/failed session 发起手动重试，复用已成功专家结果 | ✅ 已实现 |

#### Research（研究层）— `src/modules/research/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [research-technical-analyst](research-technical-analyst/spec.md) | 技术分析师：K 线指标 + LLM 定性分析 → 技术面信号 | ✅ 已实现 |
| [research-financial-auditor](research-financial-auditor/spec.md) | 财务审计员：多期财务指标 + LLM → 5D 财务健康评分 | ✅ 已实现 |
| [research-valuation-modeler](research-valuation-modeler/spec.md) | 估值建模师：分位点/PEG/Graham + LLM → 内在价值评估 | ✅ 已实现 |
| [research-macro-intelligence](research-macro-intelligence/spec.md) | 宏观情报员：Web 搜索（4 维度宏观情报）+ LLM → 宏观环境评估 | ✅ 已实现 |
| [research-catalyst-detective](research-catalyst-detective/spec.md) | 催化剂侦探：Web 搜索（4 维度催化事件）+ LLM → 催化剂评估 | ✅ 已实现 |

#### Debate（辩论层）— `src/modules/debate/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [debate-bull-bear-engine](debate-bull-bear-engine/spec.md) | 三阶段辩论：Bull ∥ Bear → Resolution → DebateOutcome | ✅ 已实现 |

#### Judge（裁决层）— `src/modules/judge/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [judge-verdict-engine](judge-verdict-engine/spec.md) | 综合裁决：BUY/SELL/HOLD + 仓位 + 止损止盈 + 风控约束 | ✅ 已实现 |

### 4.2 支撑模块

#### data_engineering — `src/modules/data_engineering/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [de-data-sync](de-data-sync/spec.md) | 统一数据同步：全量/增量/断点续跑/失败重试/配置外部化 | ✅ 已实现 |

#### llm_platform — `src/modules/llm_platform/`

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [llm-web-search](llm-web-search/spec.md) | Web 搜索网关：厂商无关 Port + 博查适配器 + WebSearchService | ✅ 已实现 |
| [web-search-cache](web-search-cache/spec.md) | 搜索结果 DB 缓存：Decorator 模式 + 按 freshness 动态 TTL | ✅ 已实现 |

### 4.3 可观测性与审计

| Spec | 一句话描述 | 归属模块 | 状态 |
|------|-----------|---------|------|
| [llm-call-audit](llm-call-audit/spec.md) | LLM 调用审计日志（prompt/completion/token/耗时/session） | llm_platform | ✅ 已实现 |
| [external-api-call-logging](external-api-call-logging/spec.md) | 外部 API 调用日志（博查搜索请求/响应/耗时/session） | llm_platform | ✅ 已实现 |
| [agent-narrative-reports](agent-narrative-reports/spec.md) | 9 个 Agent 同时产出结构化 JSON + 中文叙述性报告 | Research/Debate/Judge | ✅ 已实现 |

### 4.4 架构治理与代码质量

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [dependency-injection-root](dependency-injection-root/spec.md) | 模块级 Container（Composition Root）+ 路由精简 + main.py 解耦 | ✅ 已实现 |
| [module-config-isolation](module-config-isolation/spec.md) | 全局配置瘦身 → 模块级 BaseSettings 独立管理 | ✅ 已实现 |
| [file-naming-srp-cleanup](file-naming-srp-cleanup/spec.md) | DTO 迁出 ports/ + 文件命名对齐 + commands/queries 归属 | ✅ 已实现 |

### 4.5 健壮性与边界防御

| Spec | 一句话描述 | 状态 |
|------|-----------|------|
| [adapter-null-safety](adapter-null-safety/spec.md) | 数据适配器层 daily 空值防护 + 异常捕获收窄 | ✅ 已实现 |
| [indicator-data-sufficiency](indicator-data-sufficiency/spec.md) | 技术指标数据量门槛 + None 替代误导性默认值 | ✅ 已实现 |
| [financial-data-sanity](financial-data-sanity/spec.md) | 财务指标合理性边界校验（拦截异常毛利率等） | ✅ 已实现 |
| [research-error-consistency](research-error-consistency/spec.md) | 五专家异常类型/返回值类型/默认值统一 | ✅ 已实现 |
| [research-search-quality](research-search-quality/spec.md) | 搜索查询构造规范 + 结果过滤 + 维度级参数差异化 | ✅ 已实现 |

---

## 5. Spec 命名约定

- **`<模块>-<能力>`**：如 `debate-bull-bear-engine`、`judge-verdict-engine`
- **`research-<专家>`**：如 `research-technical-analyst`、`research-macro-intelligence`
- **横切关注点**：如 `execution-context-propagation`、`llm-call-audit`

每个 spec 目录下有且仅有一个 `spec.md`，采用统一的 WHEN/THEN Scenario 格式。

---

## 6. 相关资源

| 资源 | 路径 | 说明 |
|------|------|------|
| OpenSpec 配置 | `openspec/config.yaml` | 项目上下文摘要，创建 change 时自动注入 |
| 已归档变更 | `openspec/changes/archive/` | 已完成并归档的 16 个 change |
| 进行中变更 | `openspec/changes/` | 当前正在进行的 change |
| OpenSpec SOP | `docs/openspec-sop.md` | 使用 OpenSpec 的标准操作流程 |
| 技术规范 | [tech-standards.md](tech-standards.md) | 代码风格、响应协议、测试约定 |
| 愿景与模块 | [vision-and-modules.md](vision-and-modules.md) | 模块边界（Source of Truth） |
