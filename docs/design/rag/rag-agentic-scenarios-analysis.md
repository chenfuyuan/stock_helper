# RAG 与 Agentic RAG 结合场景全景分析

**基于项目架构**: Coordinator 编排 + 5 大专家 + Knowledge Center 知识图谱 + LLM Platform 网关

**分析维度**: 数据流向、智能层级

**日期**: 2026-03-02

---

## 目录

1. [RAG 基础场景 (检索增强生成)](#一 rag 基础场景检索增强生成)
2. [Agentic RAG 进阶场景 (多 Agent 协作 + RAG)](#二 agentic rag 进阶场景多 agent 协作 rag)
3. [场景优先级与实施难度矩阵](#三 场景优先级与实施难度矩阵)
4. [推荐实施路径](#四 推荐实施路径)
5. [具体技术方案设计](#五 具体技术方案设计)
6. [方案对比与推荐](#六 方案对比与推荐)

---

# 一、RAG 基础场景 (检索增强生成)

## 场景 1: 专家分析增强型 RAG

**核心思路**: 5 大专家在执行分析任务时，实时检索相关知识库，提升分析深度和准确性。

### 1.1 技术分析师 (Technical Analyst)

**检索内容**:
- 历史技术形态案例库 (如"头肩顶"、"双底"等经典形态的历史表现)
- 技术指标阈值参考 (不同行业/市值的合理 PE/PB 区间)
- 历史研报中的技术分析片段

**RAG 工作流**:
```
接收分析请求 → 提取股票/行业特征 → 向量检索相似历史案例 → 
拼接案例到 prompt → 生成技术分析报告
```

**价值**: 避免"凭空分析",基于历史数据提供更有说服力的判断

### 1.2 财务审计员 (Financial Auditor)

**检索内容**:
- 同行业财务指标基准值 (毛利率、净利率、周转率等)
- 财务造假典型案例库 (如"存货异常增长"、"应收账款周转率下降"等红旗信号)
- 会计准则变更影响文档

**RAG 工作流**:
```
读取财务报表 → 识别异常指标 → 检索行业基准/造假案例 → 
对比分析 → 生成审计意见
```

**价值**: 提升财务异常检测的敏感度和准确性

### 1.3 估值建模师 (Valuation Modeler)

**检索内容**:
- 历史估值倍数数据库 (不同行业/成长阶段的 PE/PB/PS/DCF 参数)
- 可比公司估值案例 (同行业并购/上市估值水平)
- 估值模型假设参考 (永续增长率、折现率等参数区间)

**RAG 工作流**:
```
读取目标公司数据 → 识别行业/成长阶段 → 检索可比估值案例 → 
校准模型参数 → 生成估值区间
```

**价值**: 避免估值参数"拍脑袋",基于市场数据校准

### 1.4 宏观情报员 (Macro Intelligence)

**检索内容**:
- 历史宏观事件影响库 (如"加息周期对 A 股各板块的影响")
- 政策文件库 (产业政策、货币政策、财政政策原文及解读)
- 宏观经济指标历史数据 (GDP、CPI、PMI 等与股市表现的相关性)

**RAG 工作流**:
```
识别当前宏观环境 → 检索历史相似时期 → 提取政策文件 → 
分析历史走势 → 生成宏观判断
```

**价值**: 基于历史规律而非主观判断

### 1.5 催化剂侦探 (Catalyst Detective)

**检索内容**:
- 历史催化剂事件库 (如"新产品发布"、"高管增持"、"并购重组"后的股价表现)
- 行业事件日历 (财报季、产品发布会、政策窗口期)
- 负面催化剂案例 (如"减持公告"、"业绩不及预期"后的跌幅统计)

**RAG 工作流**:
```
扫描公司公告/新闻 → 识别潜在催化剂 → 检索历史相似事件 → 
统计市场反应 → 生成催化剂评估
```

**价值**: 量化催化剂影响，而非定性描述

---

## 场景 2: 知识图谱增强型 RAG (Graph RAG)

**核心思路**: 利用 Knowledge Center 的 Neo4j 图谱数据，将结构化关系检索与非结构化文档检索结合。

### 2.1 图谱关系检索增强

**场景描述**: 专家分析时，不仅检索向量相似文档，还检索图谱中的关联实体

**示例**:
```
分析"宁德时代" → 
图谱检索：上游 (锂矿供应商)、下游 (车企客户)、竞争对手 (比亚迪)、投资事件 → 
向量检索：这些关联公司的研报/新闻 → 
生成分析报告
```

**价值**: 从"单点分析"升级为"产业链分析"

### 2.2 图谱路径推理

**场景描述**: 通过图谱多跳查询发现隐性关联

**示例**:
```
问题："某基金重仓的股票最近有什么风险？"
图谱查询：基金 → 重仓股 → 重仓股的供应商/客户 → 这些公司的负面新闻
发现：重仓股的某重要供应商面临诉讼风险
```

**价值**: 发现间接风险/机会，提升分析深度

### 2.3 图谱动态更新 (场景 D)

**场景描述**: 从非结构化文档抽取信息并写入图谱

**子场景**:
- **D1. 研报实体抽取**: 从研报中提取公司、人物、产品、技术路线等实体
- **D2. 关系抽取**: 提取"投资"、"合作"、"竞争"、"供应链"等关系
- **D3. 事件抽取**: 提取"并购"、"高管变动"、"产品发布"等事件并关联到时点
- **D4. 产业链构建**: 基于行业研报自动构建/完善产业链图谱

**技术流程**:
```
文档上传 → LLM 抽取实体/关系/事件 → 图谱对齐 (实体链接) → 
写入 Neo4j → 触发图谱一致性校验
```

---

## 场景 3: 跨专家知识检索

**核心思路**: 某个专家分析时，可检索其他专家的历史分析结果，形成知识复用。

### 3.1 历史专家分析复用

**场景**: 技术分析师分析时，可检索该股票过去的财务审计结果、估值结论

**示例**:
```
分析"贵州茅台" → 
检索：过去 4 个季度的财务审计意见、估值区间、催化剂事件 → 
对比当前技术面与历史基本面的关系 → 
生成分析报告
```

**价值**: 避免"重复分析",形成分析结果的累积效应

### 3.2 辩论/裁决结果检索

**场景**: 新研究请求可检索历史相似情境下的辩论结论和裁决结果

**示例**:
```
研究"新能源板块是否见顶" → 
检索：历史上其他板块"见顶"时的辩论记录、裁决依据 → 
对比当前情境 → 
生成判断
```

**价值**: 从历史决策中学习，提升系统智能

---

## 场景 4: 外部数据源 RAG

**核心思路**: 利用 LLM Platform 已有的 Web 搜索能力，结合 RAG 实现"实时信息 + 历史知识"的融合。

### 4.1 实时新闻增强

**场景**: 专家分析时，先通过 Web 搜索获取最新新闻，再与历史知识库结合

**示例**:
```
分析"某公司突发利空" → 
Web 搜索：最新新闻/公告 → 
向量检索：历史类似事件的市场反应 → 
生成分析：短期影响评估 + 历史对比
```

### 4.2 政策文件解读

**场景**: 宏观情报员分析政策时，检索政策原文 + 历史政策解读

**示例**:
```
"央行降准" → 
Web 搜索：政策原文/官方解读 → 
向量检索：历史降准后市场表现/机构解读 → 
生成宏观判断
```

---

# 二、Agentic RAG 进阶场景 (多 Agent 协作 + RAG)

**Agentic RAG 核心特征**: 不是单次"检索→生成",而是多个 Agent 通过 RAG 协作完成复杂任务，包含**规划、工具调用、反思、迭代**等 Agent 特性。

## 场景 5: 多专家协作式 Agentic RAG

**核心思路**: Coordinator 编排的 5 大专家形成 Agent 团队，共享 RAG 检索结果，进行多轮迭代分析。

### 5.1 顺序协作模式

**流程**:
```
1. 技术分析师检索历史技术形态 → 生成初步判断 → 写入共享上下文
2. 财务审计员检索技术分析师的判断 + 财务文档 → 校验基本面 → 写入共享上下文
3. 估值建模师检索前两者结论 + 估值案例 → 校准估值模型 → 写入共享上下文
4. 宏观情报员检索前三者结论 + 宏观数据 → 判断宏观环境是否支持 → 写入共享上下文
5. 催化剂侦探检索所有结论 + 事件库 → 识别近期催化剂 → 生成最终投资建议
```

**与传统 RAG 区别**: 每个 Agent 的检索内容依赖前序 Agent 的输出，形成"链式 RAG"

**价值**: 模拟真实投研团队的协作流程

### 5.2 辩论增强模式

**场景**: Debate 模块组织"多头 vs 空头"辩论时，双方 Agent 各自检索支持自己论点的知识

**流程**:
```
1. 多头 Agent 检索：利好历史案例/行业数据/政策文件
2. 空头 Agent 检索：利空历史案例/风险事件/财务异常
3. 双方基于检索结果进行多轮辩论
4. Judge 基于双方提供的检索证据进行裁决
```

**价值**: 避免"一边倒",通过对抗性检索提升决策质量

### 5.3 反思迭代模式

**场景**: 某个专家分析后，其他专家可提出质疑，触发重新检索和分析

**示例**:
```
技术分析师："技术面突破，建议买入"
财务审计员质疑："发现存货异常增长，建议重新评估"
技术分析师重新检索：历史"存货增长 + 技术突破"案例 → 修正判断
```

**Agentic 特征**: 包含"行动→观察→反思→再行动"的循环

---

## 场景 6: 图谱构建 Agent 团队 (场景 D 的 Agentic 版本)

**核心思路**: 多个 Agent 协作完成从文档到图谱的自动化构建。

### 6.1 Agent 角色分工

| Agent | 职责 | 工具/RAG 来源 |
|-------|------|--------------|
| **文档解析 Agent** | 从 PDF/Word 提取文本，识别章节结构 | OCR 工具、文档解析库 |
| **实体抽取 Agent** | 识别公司、人物、产品、行业等实体 | 检索已有实体库 (避免重复) |
| **关系抽取 Agent** | 识别实体间的投资/竞争/供应链关系 | 检索图谱现有关系 (避免冲突) |
| **事件抽取 Agent** | 识别并购、高管变动、产品发布等事件 | 检索历史事件库 (标准化表述) |
| **图谱对齐 Agent** | 将抽取的实体链接到图谱现有节点 | Neo4j 图谱查询 |
| **质量校验 Agent** | 检查关系一致性、实体去重、冲突检测 | 图谱约束规则库 |

### 6.2 协作流程

```
1. 文档解析 Agent 输出结构化文本
2. 实体/关系/事件 Agent 并行抽取 (可多轮迭代)
3. 图谱对齐 Agent 进行实体链接
   - 发现"宁德时代"已存在 → 链接到现有节点
   - 发现"CATL"不存在 → 创建新节点并建立别名
4. 质量校验 Agent 检查
   - 发现冲突："A 投资 B"vs"B 投资 A" → 触发人工审核
5. 写入 Neo4j
```

**Agentic 特征**: 多 Agent 分工、工具调用、冲突检测、迭代优化

---

## 场景 7: 研究规划 Agent (Meta-Agent)

**核心思路**: 一个高层 Agent 负责规划"需要检索什么知识→调用哪些专家→如何整合结果"。

### 7.1 动态研究规划

**用户问题**: "现在是否适合买入新能源板块？"

**研究规划 Agent 的分析过程**:

**1. 问题拆解**:
- 需要技术面分析 → 调用技术分析师
- 需要基本面分析 → 调用财务审计员 + 估值建模师
- 需要宏观环境判断 → 调用宏观情报员
- 需要催化剂判断 → 调用催化剂侦探

**2. 知识检索规划**:
- 检索新能源板块历史走势案例
- 检索当前行业估值水平
- 检索最新政策文件
- 检索产业链上下游动态

**3. 执行计划**:
- 先并行检索知识库
- 将检索结果分发给各专家
- 组织专家进行辩论
- 生成最终投资建议

**Agentic 特征**: 任务规划、工具编排、动态决策

### 7.2 自适应检索策略

**场景**: 根据问题复杂度动态调整检索深度

**示例**:
```
简单问题："某公司今天股价多少？" → 直接查询数据库，无需 RAG
中等问题："某公司技术面如何？" → 单次 RAG 检索 + 技术分析
复杂问题："现在是否适合买入某股票？" → 多轮 RAG + 多专家协作 + 辩论
```

**价值**: 平衡响应速度和答案质量

---

## 场景 8: 自我进化型 Agentic RAG

**核心思路**: 系统通过分析历史成功/失败案例，不断优化 RAG 检索策略和 Agent 协作模式。

### 8.1 案例库构建

**自动记录**: 每次研究的完整链路
- 检索了哪些文档
- 调用了哪些专家
- 辩论过程如何
- 最终裁决结果
- 事后市场验证 (如"买入建议后 1 个月实际涨幅")

### 8.2 策略优化 Agent

**职责**: 定期分析案例库，发现规律

**示例发现**:
```
发现 1: "当检索'财务造假案例'时，财务审计员的准确率提升 30%"
  → 优化策略：财务分析时强制检索造假案例库

发现 2: "当技术分析师和宏观情报员结论相反时，最终裁决错误率较高"
  → 优化策略：这种情况下触发更多轮辩论

发现 3: "检索超过 5 篇文档后，答案质量不再提升"
  → 优化策略：限制最大检索文档数，提升效率
```

**Agentic 特征**: 元认知、自我反思、策略优化

---

## 场景 9: 人机协作型 Agentic RAG

**核心思路**: 用户可介入 Agent 的 RAG 过程，提供反馈或指导检索方向。

### 9.1 交互式检索

**示例**:
```
用户："分析一下宁德时代"

系统：已检索以下文档:
  1. 宁德时代 2025 年报
  2. 动力电池行业研报
  3. 历史技术形态案例

用户："请补充检索'宁德时代海外扩张'相关信息"

系统：已补充检索:
  4. 宁德时代德国工厂进展
  5. 与特斯拉海外合作新闻
  6. 海外竞争对手分析

→ 继续生成分析报告
```

**价值**: 用户可引导分析方向，避免"答非所问"

### 9.2 反馈学习

```
用户对分析报告标注:
  - "这个结论很有说服力" (点赞某段检索结果)
  - "这个案例不相关" (点踩某段检索结果)

系统记录反馈 → 优化未来检索排序策略
```

---

# 三、场景优先级与实施难度矩阵

| 场景编号 | 场景名称 | 业务价值 | 实施难度 | 依赖基础 |
|---------|---------|---------|---------|---------|
| 1.1-1.5 | 专家分析增强型 RAG | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 向量数据库、文档库 |
| 2.1-2.2 | 图谱关系检索增强 | ⭐⭐⭐⭐ | ⭐⭐⭐ | Knowledge Center 图谱 |
| 2.3 | 图谱动态更新 (D) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 实体/关系抽取模型 |
| 3.1-3.2 | 跨专家知识检索 | ⭐⭐⭐⭐ | ⭐⭐ | 已有专家结果存储 |
| 4.1-4.2 | 外部数据源 RAG | ⭐⭐⭐⭐ | ⭐⭐ | LLM Platform Web 搜索 |
| 5.1-5.3 | 多专家协作 Agentic RAG | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Coordinator 编排 |
| 6.1-6.2 | 图谱构建 Agent 团队 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 多 Agent 协作框架 |
| 7.1-7.2 | 研究规划 Agent | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 规划/反思能力 |
| 8.1-8.2 | 自我进化型 RAG | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 案例库 + 策略学习 |
| 9.1-9.2 | 人机协作 RAG | ⭐⭐⭐⭐ | ⭐⭐⭐ | 交互界面 |

---

# 四、推荐实施路径

基于你的项目现状 (已有 Coordinator 编排、Knowledge Center 图谱、LLM Platform 网关),我建议分三阶段实施:

## 第一阶段 (快速见效): 基础 RAG 增强

**目标**: 为 5 大专家实现基础 RAG 能力

**范围**: 场景 1.1-1.5 + 场景 4.1-4.2

**核心工作**:
1. 搭建向量数据库 (如 Qdrant/Milvus)
2. 文档入库 (历史研报、财务文档、行业数据)
3. 专家模块集成 RAG 检索接口
4. 利用 LLM Platform 的 Web 搜索能力

**周期**: 2-3 周

**价值**: 快速提升专家分析质量

## 第二阶段 (差异化优势): Graph RAG + 跨专家检索

**目标**: 结合图谱和跨专家知识

**范围**: 场景 2.1-2.2 + 场景 3.1-3.2

**核心工作**:
1. 扩展 Knowledge Center 查询接口
2. 实现"图谱关系检索 + 向量检索"混合检索
3. 建立专家分析结果存储和检索机制

**周期**: 3-4 周

**价值**: 形成独特的"图谱+RAG"能力

## 第三阶段 (长期演进): Agentic RAG

**目标**: 实现多 Agent 协作和自我进化

**范围**: 场景 5.1-5.3 + 场景 6.1-6.2 + 场景 8.1-8.2

**核心工作**:
1. 扩展 Coordinator 支持多轮迭代
2. 构建图谱构建 Agent 团队
3. 建立案例库和策略优化机制

**周期**: 6-8 周

**价值**: 达到行业领先的 Agentic RAG 能力

---

# 五、具体技术方案设计

基于前面的场景分析，我为你设计 3 个不同切入点的方案，每个方案都包含**架构设计**、**核心组件**、**实施步骤**和**权衡分析**。

## 方案 A: 专家增强型 RAG (从场景 1 切入)

**方案定位**: 为现有 5 大专家快速集成 RAG 能力，最小改动、快速见效。

### A.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   Coordinator Layer                     │
│  (LangGraph 编排：动态调用 5 大专家)                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Expert Layer (增强后)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Technical     │  │Financial     │  │Valuation     │  │
│  │Analyst +RAG  │  │Auditor +RAG  │  │Modeler +RAG  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │Macro         │  │Catalyst      │                     │
│  │Intelligence  │  │Detective     │                     │
│  │+RAG          │  │+RAG          │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    RAG Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │Vector Search    │  │Web Search       │              │
│  │(Qdrant/Milvus)  │  │(Bocha API)      │              │
│  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────────────────────────────┐          │
│  │Knowledge Repositories:                  │          │
│  │- 历史研报库 (PDF/Markdown)               │          │
│  │- 财务文档库 (年报/季报)                  │          │
│  │- 行业数据库 (估值倍数/技术指标)           │          │
│  │- 案例库 (催化剂/宏观事件)                │          │
│  └─────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

### A.2 核心组件

#### 组件 1: RAG 检索服务 (新增模块)

```python
# src/modules/rag/application/services/retrieval_service.py

class RetrievalService:
    """RAG 检索服务，为专家提供统一的检索接口。"""
    
    async def retrieve_for_expert(
        self,
        expert_type: ExpertType,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[RAGDocument]:
        """
        根据专家类型和查询词检索相关文档。
        
        不同专家类型映射到不同的知识库:
        - TECHNICAL_ANALYST → 技术形态案例库 + 指标阈值库
        - FINANCIAL_AUDITOR → 财务基准库 + 造假案例库
        - VALUATION_MODELER → 估值案例库 + 可比公司库
        - MACRO_INTELLIGENCE → 宏观事件库 + 政策文件库
        - CATALYST_DETECTIVE → 催化剂事件库
        """
        # 1. 根据 expert_type 选择知识库
        # 2. 向量检索 (Qdrant/Milvus)
        # 3. 可选：混合检索 (向量 + BM25)
        # 4. 重排序 (Cross-Encoder)
        # 5. 返回 top-k 文档
```

#### 组件 2: 专家模块集成 (扩展现有服务)

```python
# src/modules/research/application/services/technical_analyst_service.py (增强后)

class TechnicalAnalystService:
    def __init__(
        self,
        technical_analysis_port: ITechnicalAnalysisPort,
        retrieval_service: RetrievalService,  # 新增依赖
    ) -> None:
        self._retrieval_service = retrieval_service
    
    async def analyze(
        self,
        symbol: str,
        options: dict[str, Any] | None = None,
    ) -> TechnicalAnalysisResult:
        # 1. 生成检索查询词
        query = self._build_query(symbol, options)
        
        # 2. RAG 检索 (新增)
        docs = await self._retrieval_service.retrieve_for_expert(
            expert_type=ExpertType.TECHNICAL_ANALYST,
            query=query,
        )
        
        # 3. 拼接检索结果到 prompt
        context = self._build_context(docs)
        
        # 4. 调用 LLM (已有逻辑)
        result = await self._llm_service.generate(
            prompt=f"{context}\n\n请分析 {symbol} 的技术面...",
        )
        
        return result
```

#### 组件 3: 文档入库工具 (一次性脚本)

```python
# scripts/ingest_documents.py

async def ingest_documents():
    """批量导入文档到向量数据库。"""
    # 1. 扫描文档目录 (PDF/Markdown/Word)
    # 2. 文本提取 (PyPDF2/python-docx)
    # 3. 分块 (按章节/固定长度)
    # 4. 生成 embedding (调用 LLM Platform)
    # 5. 写入向量数据库
    # 6. 建立元数据索引 (专家类型/行业/日期)
```

### A.3 实施步骤

| 步骤 | 工作内容 | 预计时间 |
|-----|---------|---------|
| 1 | 选型并部署向量数据库 (Qdrant/Milvus) | 2 天 |
| 2 | 实现 RetrievalService 核心检索逻辑 | 3 天 |
| 3 | 文档入库工具开发 + 历史文档导入 | 3 天 |
| 4 | 5 大专家服务集成 RAG 检索 | 5 天 |
| 5 | 测试与调优 (检索质量/响应时间) | 3 天 |
| **总计** | | **~2-3 周** |

### A.4 方案优势

- ✅ **改动最小**: 不改变现有 Coordinator 编排逻辑
- ✅ **快速见效**: 2-3 周可上线
- ✅ **风险可控**: 每个专家独立集成，互不影响
- ✅ **可渐进优化**: 后续可叠加 Graph RAG/Agentic RAG

### A.5 方案局限

- ❌ **知识孤岛**: 各专家独立检索，无法共享上下文
- ❌ **无图谱能力**: 未利用 Knowledge Center 的图谱优势
- ❌ **单次检索**: 不支持多轮迭代检索

---

## 方案 B: Graph RAG 融合方案 (从场景 2 切入)

**方案定位**: 结合 Knowledge Center 的图谱能力，实现"图谱关系检索 + 向量检索"的混合 RAG。

### B.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   Coordinator Layer                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Expert Layer                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Hybrid RAG Layer                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Query Understanding & Routing                   │   │
│  │  - 识别查询中的实体 (公司/行业/人物)              │   │
│  │  - 判断是否需要图谱检索                          │   │
│  └─────────────────────────────────────────────────┘   │
│           ↓                      ↓                      │
│  ┌─────────────────┐    ┌─────────────────┐           │
│  │ Graph Search    │    │ Vector Search   │           │
│  │ (Neo4j)         │    │ (Qdrant)        │           │
│  │ - 实体关联检索   │    │ - 语义相似文档   │           │
│  │ - 多跳路径查询   │    │ - 全文检索       │           │
│  │ - 子图匹配      │    │                 │           │
│  └─────────────────┘    └─────────────────┘           │
│           ↓                      ↓                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Fusion & Re-ranking                   │   │
│  │   - 合并图谱结果 + 向量结果                      │   │
│  │   - 去重、加权、重排序                          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### B.2 核心组件

#### 组件 1: 图谱检索服务 (扩展 Knowledge Center)

```python
# src/modules/knowledge_center/application/services/graph_retrieval_service.py

class GraphRetrievalService:
    """基于图谱的检索服务。"""
    
    async def retrieve_related_entities(
        self,
        entity_id: str,
        relation_types: list[RelationshipType] | None = None,
        max_hops: int = 2,
    ) -> list[GraphEntity]:
        """
        检索实体的关联实体。
        
        示例:
        - 输入：entity_id="宁德时代", relation_types=["SUPPLIER", "CUSTOMER"], max_hops=1
        - 输出：[锂矿供应商，车企客户，...]
        """
        # Cypher 查询 Neo4j
        
    async def retrieve_entity_context(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """
        获取实体的完整上下文 (一度/二度关联 + 关联的文档)。
        
        用于 RAG 场景：分析"宁德时代"时，检索其产业链上下游 + 相关新闻/研报
        """
        # 1. 查询实体属性
        # 2. 查询关联实体 (多跳)
        # 3. 查询关联的文档 (图谱中的文档链接)
        # 4. 拼接为结构化上下文
```

#### 组件 2: 混合检索路由器

```python
# src/modules/rag/application/services/hybrid_retrieval_service.py

class HybridRetrievalService:
    """混合检索服务：图谱检索 + 向量检索。"""
    
    async def retrieve(
        self,
        query: str,
        expert_type: ExpertType,
        top_k: int = 10,
    ) -> list[RAGDocument]:
        # 1. Query Understanding
        entities = await self._extract_entities(query)
        # 识别查询中的实体 (如"宁德时代的供应商")
        
        # 2. 图谱检索 (如果识别到实体)
        graph_results = []
        if entities:
            graph_results = await self._graph_service.retrieve_entity_context(
                entities[0].id,
            )
        
        # 3. 向量检索 (总是执行)
        vector_results = await self._vector_service.search(
            query=query,
            filters={"expert_type": expert_type.value},
            top_k=top_k,
        )
        
        # 4. 融合 & 重排序
        fused = self._fuse_results(graph_results, vector_results)
        reranked = await self._rerank(fused, query)
        
        return reranked[:top_k]
    
    def _fuse_results(
        self,
        graph_results: list,
        vector_results: list,
    ) -> list:
        """
        融合策略:
        - 图谱结果权重更高 (结构化知识更可靠)
        - 去重 (图谱和向量结果可能有重叠)
        - 多样性 (避免单一来源)
        """
```

#### 组件 3: 图谱动态更新 Agent (场景 D)

```python
# src/modules/knowledge_center/application/services/document_ingestion_service.py

class DocumentIngestionService:
    """文档入库服务：从非结构化文档抽取信息并写入图谱。"""
    
    async def ingest_document(
        self,
        document: Document,
        auto_commit: bool = False,
    ) -> IngestionResult:
        # 1. 实体抽取 (LLM)
        entities = await self._extract_entities(document.text)
        
        # 2. 关系抽取 (LLM)
        relations = await self._extract_relations(entities, document.text)
        
        # 3. 实体链接 (对齐到现有图谱)
        linked_entities = await self._link_entities(entities)
        
        # 4. 冲突检测
        conflicts = await self._detect_conflicts(linked_entities, relations)
        if conflicts and not auto_commit:
            return IngestionResult(
                status="pending_review",
                conflicts=conflicts,
            )
        
        # 5. 写入 Neo4j
        await self._graph_repository.upsert_entities(linked_entities)
        await self._graph_repository.upsert_relations(relations)
        
        # 6. 向量化文档内容 (用于后续向量检索)
        await self._vector_service.index_document(document)
        
        return IngestionResult(status="success")
```

### B.3 实施步骤

| 步骤 | 工作内容 | 预计时间 |
|-----|---------|---------|
| 1 | 扩展 Knowledge Center 查询接口 | 3 天 |
| 2 | 实现 GraphRetrievalService | 3 天 |
| 3 | 实现 HybridRetrievalService(融合/重排序) | 4 天 |
| 4 | 文档入库服务开发 (实体/关系抽取) | 5 天 |
| 5 | 专家模块集成混合检索 | 3 天 |
| 6 | 测试与调优 | 3 天 |
| **总计** | | **~3-4 周** |

### B.4 方案优势

- ✅ **差异化优势**: 结合图谱的 RAG 是行业前沿方向
- ✅ **知识关联**: 发现隐性关系 (如产业链传导效应)
- ✅ **可解释性**: 图谱路径提供清晰的推理链
- ✅ **场景 D 支持**: 自动化构建图谱，减少人工维护

### B.5 方案局限

- ❌ **依赖图谱质量**: 图谱不完整时效果受限
- ❌ **实现复杂度**: 需要同时维护图谱和向量索引
- ❌ **查询延迟**: 多跳图谱查询可能较慢

---

## 方案 C: Agentic RAG 协作方案 (从场景 5 切入)

**方案定位**: 基于现有 Coordinator 编排能力，实现多专家协作的 Agentic RAG。

### C.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│              Agentic RAG Orchestrator                   │
│  (扩展 Coordinator: 支持多轮迭代 + 共享上下文)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Shared Context Manager                     │
│  - 存储检索结果 (所有专家共享)                           │
│  - 存储中间分析结果                                      │
│  - 支持版本控制 (每轮迭代更新)                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Expert Team (5 大专家 + RAG)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Technical     │→ │Financial     │→ │Valuation     │  │
│  │Analyst       │  │Auditor       │  │Modeler       │  │
│  │(可读取前序   │  │(可读取前序   │  │(可读取前序   │  │
│  │  专家结论)   │  │  专家结论)   │  │  专家结论)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                          ↓                              │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │Debate Agent  │← │Macro &       │                     │
│  │(组织辩论)    │  │Catalyst      │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Reflection & Iteration                     │
│  - 检测结论冲突 → 触发重新检索                           │
│  - 检测知识不足 → 补充检索                               │
│  - 达到收敛条件 → 进入辩论/裁决                          │
└─────────────────────────────────────────────────────────┘
```

### C.2 核心组件

#### 组件 1: 共享上下文管理器

```python
# src/modules/coordinator/application/services/context_manager.py

class SharedContextManager:
    """管理多专家协作的共享上下文。"""
    
    def __init__(self, session_id: UUID) -> None:
        self._session_id = session_id
        self._context: dict[str, Any] = {
            "retrieved_docs": [],  # 所有检索结果
            "expert_analyses": {},  # 各专家分析结果
            "conflicts": [],  # 检测到的冲突
            "iteration_count": 0,
        }
    
    async def add_retrieval_results(
        self,
        docs: list[RAGDocument],
        source: str,
    ) -> None:
        """添加检索结果 (去重后合并)。"""
        
    async def add_expert_analysis(
        self,
        expert_type: str,
        analysis: ExpertResult,
    ) -> None:
        """添加专家分析结果。"""
        
    async def detect_conflicts(self) -> list[Conflict]:
        """
        检测专家结论之间的冲突。
        
        示例冲突:
        - 技术分析师："技术面突破，建议买入"
        - 财务审计员："发现财务异常，建议谨慎"
        """
        
    def get_context_for_expert(
        self,
        expert_type: str,
    ) -> dict[str, Any]:
        """
        为指定专家生成上下文 (包含前序专家结论)。
        
        用于链式协作：后序专家可读取前序专家的分析结果
        """
```

#### 组件 2: 迭代控制器

```python
# src/modules/coordinator/infrastructure/orchestration/iteration_controller.py

class IterationController:
    """控制 Agentic RAG 的多轮迭代。"""
    
    async def should_continue(
        self,
        context: SharedContextManager,
        max_iterations: int = 3,
    ) -> tuple[bool, str]:
        """
        判断是否继续迭代。
        
        收敛条件:
        1. 达到最大迭代次数
        2. 所有专家结论一致 (无冲突)
        3. 检索结果已饱和 (新增检索不再提供新信息)
        4. 置信度达到阈值
        
        返回：(是否继续，原因)
        """
        
    async def plan_next_iteration(
        self,
        context: SharedContextManager,
    ) -> IterationPlan:
        """
        规划下一轮迭代。
        
        示例计划:
        - 需要重新检索：财务审计员发现异常，需补充检索"财务造假案例"
        - 需要新增专家：当前缺少宏观环境分析，调用宏观情报员
        - 需要辩论：技术面 vs 基本面结论冲突
        """
```

#### 组件 3: 辩论增强 (扩展现有 Debate 模块)

```python
# src/modules/debate/application/services/debate_service.py (增强后)

class DebateService:
    async def run_debate(
        self,
        symbol: str,
        expert_results: dict[str, ExpertResult],
        context: SharedContextManager | None = None,  # 新增
    ) -> DebateOutcome:
        """
        组织辩论 (支持 RAG 增强)。
        
        增强点:
        1. 多头/空头 Agent 各自检索支持自己论点的文档
        2. 基于检索结果进行多轮辩论
        3. Judge 基于双方提供的检索证据进行裁决
        """
        # 1. 多头检索
        bull_docs = await self._retrieval_service.retrieve(
            query=self._build_bull_query(expert_results),
            perspective="bull",
        )
        
        # 2. 空头检索
        bear_docs = await self._retrieval_service.retrieve(
            query=self._build_bear_query(expert_results),
            perspective="bear",
        )
        
        # 3. 多轮辩论 (每轮可补充检索)
        # ...
```

### C.3 实施步骤

| 步骤 | 工作内容 | 预计时间 |
|-----|---------|---------|
| 1 | 实现 SharedContextManager | 3 天 |
| 2 | 实现 IterationController | 4 天 |
| 3 | 扩展 Coordinator 支持迭代编排 | 5 天 |
| 4 | 专家服务改造 (支持读取共享上下文) | 4 天 |
| 5 | 辩论模块 RAG 增强 | 3 天 |
| 6 | 测试与调优 | 4 天 |
| **总计** | | **~4-5 周** |

### C.4 方案优势

- ✅ **模拟真实投研流程**: 多专家协作、辩论、迭代
- ✅ **决策质量更高**: 通过对抗性检索减少偏见
- ✅ **可解释性强**: 完整的推理链和证据链
- ✅ **可扩展**: 后续可加入自我进化/人机协作

### C.5 方案局限

- ❌ **实现复杂度高**: 需要改造 Coordinator 核心逻辑
- ❌ **响应时间长**: 多轮迭代增加延迟
- ❌ **调试困难**: Agent 协作流程不易排查问题

---

# 六、方案对比与推荐

## 方案对比总览

| 维度 | 方案 A: 专家增强 RAG | 方案 B: Graph RAG 融合 | 方案 C: Agentic RAG 协作 |
|-----|---------------------|----------------------|------------------------|
| **实施周期** | 2-3 周 | 3-4 周 | 4-5 周 |
| **技术难度** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **业务价值** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **差异化优势** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **与现有架构兼容性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **后续扩展性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 我的推荐：分阶段实施 A → B → C

**理由**:

1. **方案 A 快速验证**: 2-3 周内让 RAG 能力上线，验证业务价值
2. **方案 B 构建壁垒**: 结合图谱的 RAG 是你的独特优势，需要重点投入
3. **方案 C 长期演进**: Agentic RAG 是行业趋势，但需要前两个方案打基础

## 关键决策点

| 情况 | 推荐方案 | 说明 |
|-----|---------|------|
| **时间紧迫** (1 个月内上线) | 只做方案 A | 快速验证 RAG 价值 |
| **追求差异化** | 方案 A + B 同步 | 投入增加 1 周，形成"图谱+RAG"特色 |
| **面向未来** | 三阶段全面推进 | 总周期 2-3 个月，达到行业领先 |

---

# 七、总结

## 核心洞察

1. **你的项目具备得天独厚的 RAG 实施条件**:
   - Coordinator 编排能力 → 天然支持多专家协作
   - Knowledge Center 图谱 → Graph RAG 的基础设施
   - LLM Platform 网关 → 统一的 LLM 调用和 Web 搜索

2. **RAG 和 Agentic RAG 不是二选一，而是演进阶梯**:
   - 基础 RAG (场景 1-4): 快速提升专家分析质量
   - Graph RAG (场景 2): 构建差异化优势
   - Agentic RAG (场景 5-9): 长期演进方向

3. **实施策略建议**:
   - 不要一开始就追求复杂的 Agentic RAG
   - 从方案 A 开始，快速验证价值
   - 逐步叠加 Graph RAG 和 Agentic 能力
   - 保持架构的可扩展性，为未来留空间

## 下一步行动

根据你的时间和资源情况，选择以下路径之一:

1. **快速启动**: 从方案 A 开始，搭建向量数据库，为 5 大专家集成基础 RAG
2. **差异化路线**: 方案 A + B 同步，充分利用 Knowledge Center 的图谱优势
3. **全面规划**: 制定 2-3 个月的演进路线图，分阶段实施

---

**文档版本**: v1.0  
**创建日期**: 2026-03-02  
**作者**: AI Architect Assistant
