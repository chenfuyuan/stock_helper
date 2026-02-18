---
title: Macro Intelligence Specification
version: 1.0
last_updated: 2026-02-19
module: research
capabilities:
  - macro-analysis
source_specs:
  - research-macro-intelligence
---

# Macro Intelligence Specification

## Purpose

宏观情报员能力：从自上而下视角，通过 Web 搜索获取实时宏观动态（货币政策、产业政策、宏观经济周期、行业景气），结合 LLM 进行定性分析，输出结构化的宏观环境评估（Favorable / Neutral / Unfavorable + 四维分析 JSON），供 Debate/Judge 使用。Research 对 Coordinator 按专家暴露独立 Application 接口，本 spec 仅约束宏观情报员。

**核心特点**：这是 Research 五专家中唯一以**软情报（Web 搜索）**为主要数据源的角色。系统基于标的行业上下文动态生成搜索查询，按四个维度获取实时宏观情报，LLM 仅基于搜索结果进行定性分析，**禁止引用搜索结果中未出现的数据或事件**。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| macro-analysis | 宏观环境分析与评估 | research-macro-intelligence/spec.md |

## General Conventions

### Requirement Language
- **SHALL** / **MUST**：强制性要求
- **SHOULD**：推荐性要求
- **MAY**：可选要求

### Testing Convention
每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## capability: macro-analysis

> Source: research-macro-intelligence/spec.md

宏观情报员能力：通过 Web 搜索获取实时宏观动态，结合 LLM 进行定性分析，输出结构化的宏观环境评估。

---

## Requirements

### Requirement: 宏观情报员暴露独立 Application 接口

Research 模块 SHALL 为宏观情报员暴露独立的 Application 层入口（如 `MacroIntelligenceService`），供 Coordinator 直接调用。该接口 SHALL NOT 与其他四专家共用同一入口；Coordinator 编排时 SHALL 分别调用各专家的专属 Application 接口。

#### Scenario: Coordinator 调用宏观情报员

- **WHEN** Coordinator 需要该标的的宏观面评估
- **THEN** Coordinator 调用宏观情报员的 Application 接口（入参含 symbol），获得宏观分析结果 DTO，且不通过统一的「Research 总入口」

#### Scenario: 接口入参与出参为 DTO

- **WHEN** 调用宏观情报员 Application 接口
- **THEN** 入参为 DTO 或值对象（至少包含 symbol），出参为宏观分析结果 DTO（对应下方输出契约），不暴露 Research 内部领域模型

---

### Requirement: 输入契约 — 股票代码与多源数据自动获取

宏观情报员 SHALL 接受股票代码（symbol）作为主要输入。系统 SHALL 自动：
1. 从 data_engineering 获取该标的的**股票基础信息**（名称 stock_name、行业 industry、代码 third_code）—— 通过已有的 `GetStockBasicInfoUseCase`。
2. 基于行业与公司上下文，通过 llm_platform 的 `WebSearchService` 执行**多主题宏观搜索**，获取实时宏观情报。

宏观情报员 SHALL NOT 在观点中引用或捏造 Web 搜索结果中不存在的数据或事件。

（其余内容省略，完整内容参考原始 spec）
