---
title: Error Consistency Specification
version: 1.0
last_updated: 2026-02-19
module: research
capabilities:
  - error-consistency
source_specs:
  - research-error-consistency
---

# Error Consistency Specification

## Purpose

统一五个专家 Application Service 的异常类型、返回值类型与默认值规范，降低 Coordinator 侧的兼容处理成本。涉及 CatalystDetectiveService、FinancialAuditorService、ValuationModelerService 及 ResearchGatewayAdapter。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| error-consistency | 异常与返回值统一规范 | research-error-consistency/spec.md |

## General Conventions

### Requirement Language
- **SHALL** / **MUST**：强制性要求
- **SHOULD**：推荐性要求
- **MAY**：可选要求

### Testing Convention
每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## capability: error-consistency

> Source: research-error-consistency/spec.md

统一五个专家 Application Service 的异常类型、返回值类型与默认值规范。

---

## Requirements

### Requirement: 异常类型统一

五个专家 Application Service 在遇到"标的不存在"或"搜索全部失败"等业务异常时，SHALL 统一使用 `BadRequestException`（来自 `src/shared/domain/exceptions.py`），不使用各模块自定义的 `StockNotFoundError`、`CatalystSearchError` 等。保持 Coordinator 侧异常捕获的一致性。

（其余内容省略，完整内容参考原始 spec）
