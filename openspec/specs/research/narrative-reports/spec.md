---
title: Narrative Reports Specification
version: 1.0
last_updated: 2026-02-19
module: research
capabilities:
  - narrative-reports
source_specs:
  - agent-narrative-reports
---

# Narrative Reports Specification

## Purpose

Agent 双输出与叙述性报告：所有 9 个 Agent（5 个 Research 专家 + Bull/Bear/Resolution + Judge Verdict）在单次 LLM 调用中同时产出结构化 JSON 与中文叙述性报告；各结果 DTO 新增 narrative_report 字段，Prompt 与 output_parser 同步改造并兼容缺失字段的降级。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| narrative-reports | 叙述性报告生成 | agent-narrative-reports/spec.md |

## General Conventions

### Requirement Language
- **SHALL** / **MUST**：强制性要求
- **SHOULD**：推荐性要求
- **MAY**：可选要求

### Testing Convention
每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## capability: narrative-reports

> Source: agent-narrative-reports/spec.md

Agent 双输出与叙述性报告：所有 9 个 Agent 在单次 LLM 调用中同时产出结构化 JSON 与中文叙述性报告。

---

## Requirements

### Requirement: Agent 双输出模式

所有 9 个 Agent（5 个 Research 专家 + Bull/Bear/Resolution + Judge Verdict）的 LLM 调用 SHALL 在单次调用中同时产出结构化 JSON 数据和叙述性中文报告。

结构化 JSON 中 MUST 新增 `narrative_report` 字段（string 类型），包含面向人类的中文分析报告。

（其余内容省略，完整内容参考原始 spec）
