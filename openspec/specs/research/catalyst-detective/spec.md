---
title: Catalyst Detective Specification
version: 1.0
last_updated: 2026-02-19
module: research
capabilities:
  - catalyst-detection
source_specs:
  - research-catalyst-detective
---

# Catalyst Detective Specification

## Purpose

催化剂侦探能力：从自下而上视角，通过 Web 搜索识别可能触发标的股价显著变动的具体催化事件（公司重大动态、行业事件、市场情绪变化、业绩预期变化），结合 LLM 进行定性分析，输出结构化的催化剂评估（Positive / Neutral / Negative + 四维分析 + 正面/负面催化事件清单 JSON），供 Debate/Judge 使用。Research 对 Coordinator 按专家暴露独立 Application 接口，本 spec 仅约束催化剂侦探。

**核心特点**：这是 Research 五专家中第二位以**软情报（Web 搜索）**为主要数据源的角色（第一位为宏观情报员）。与宏观情报员的行业级宏观视角不同，催化剂侦探聚焦**个股级事件驱动因子**，搜索查询包含**公司名称**以聚焦标的相关催化事件。LLM 仅基于搜索结果进行定性分析，**禁止引用搜索结果中未出现的事件或数据**。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| catalyst-detection | 催化事件识别与评估 | research-catalyst-detective/spec.md |

## General Conventions

### Requirement Language
- **SHALL** / **MUST**：强制性要求
- **SHOULD**：推荐性要求
- **MAY**：可选要求

### Testing Convention
每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## capability: catalyst-detection

> Source: research-catalyst-detective/spec.md

催化剂侦探能力：通过 Web 搜索识别可能触发标的股价显著变动的具体催化事件。

---

## Requirements

（内容省略，完整内容参考原始 spec）
