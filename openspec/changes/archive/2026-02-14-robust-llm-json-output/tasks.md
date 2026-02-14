## 1. 基础设施：通用异常与统一处理器

- [x] 1.1 在 `src/shared/domain/exceptions.py` 中新增 `LLMJsonParseError`（继承 `AppException`），携带 `message`、`details`（含 `raw_length`、`json_error`、`validation_errors` 等可选键）
- [x] 1.2 创建 `src/shared/infrastructure/llm_json_parser.py`，实现 `parse_llm_json_output[T]` 纯函数：空值检查 → strip think 标签 → strip markdown 代码块 → 修复控制字符 → json.loads → fallback { } 提取 → 根节点类型检查 → 归一化钩子 → Pydantic model_validate。失败时抛 `LLMJsonParseError`，日志含 `context_label`
- [x] 1.3 在同文件中实现 `generate_and_parse[T]` 异步函数：调用 llm_call → parse_llm_json_output → 失败时构造含错误信息的修正 prompt 重试 → 重试耗尽抛 LLMJsonParseError；LLM 调用异常（非解析异常）直接透传不重试
- [x] 1.4 为 `parse_llm_json_output` 编写单元测试，覆盖 spec `unified-llm-output-parser` 的全部 Scenario（纯净 JSON、markdown 包裹、think 标签、前后说明文字、控制字符、非法内容、空返回、数组根节点、字段校验成功/失败、归一化钩子、钩子异常、context_label 日志）
- [x] 1.5 为 `generate_and_parse` 编写单元测试（mock llm_call），覆盖 spec `llm-json-retry` 的全部 Scenario（首次成功、首次失败重试成功、多次重试、重试耗尽、max_retries=0、LLM 连接异常透传、重试中连接异常、重试日志）

## 2. Research 模块：5 个 Agent output_parser 迁移

- [x] 2.1 重构 `research/infrastructure/agents/macro_intelligence/output_parser.py`：`parse_macro_intelligence_result` 委托 `parse_llm_json_output(raw, MacroIntelligenceResultDTO, context_label="宏观情报员")`，捕获 `LLMJsonParseError` 转为 research 模块的 `LLMOutputParseError`
- [x] 2.2 重构 `research/infrastructure/agents/financial_auditor/output_parser.py`：同上模式，`context_label="财务审计员"`
- [x] 2.3 重构 `research/infrastructure/agents/valuation_modeler/output_parser.py`：委托时传入 `normalizers=[_normalize_verdict]`（verdict 枚举映射钩子），`context_label="估值建模师"`
- [x] 2.4 重构 `research/infrastructure/agents/catalyst_detective/output_parser.py`：`context_label="催化剂侦探"`
- [x] 2.5 重构 `research/infrastructure/agents/technical_analyst/output_parser.py`：`context_label="技术分析师"`
- [x] 2.6 将 `research/infrastructure/llm_output_utils.py` 标记为 deprecated（添加模块级 deprecation 注释），确认无其他调用方后可在后续版本删除
- [x] 2.7 验证 Research 模块 5 个 Agent 的现有测试全部通过（重构后公开函数签名不变，Adapter 代码无需修改）

## 3. Debate 模块：3 个 Agent output_parser 迁移

- [x] 3.1 重构 `debate/infrastructure/agents/bull_advocate/output_parser.py`：委托时传入 `normalizers=[_normalize_bull_fields]`（supporting_arguments + acknowledged_risks + price_catalysts 归一化钩子），`context_label="多头辩护人"`
- [x] 3.2 重构 `debate/infrastructure/agents/bear_advocate/output_parser.py`：委托时传入 `normalizers=[_normalize_bear_fields]`（supporting_arguments + acknowledged_strengths + risk_triggers 归一化钩子），`context_label="空头辩护人"`
- [x] 3.3 重构 `debate/infrastructure/agents/resolution/output_parser.py`：`context_label="冲突消解"`
- [x] 3.4 验证 Debate 模块 3 个 Agent 的现有测试全部通过

## 4. Judge 模块：1 个 Agent output_parser 迁移

- [x] 4.1 重构 `judge/infrastructure/agents/verdict/output_parser.py`：`context_label="最终裁决"`
- [x] 4.2 验证 Judge 模块现有测试全部通过

## 5. 集成验证

- [x] 5.1 在 Docker 环境中运行全量测试（`docker compose exec app pytest`），确认无回归（本地 70/70 相关测试通过；4 个 failure 和 13 个 error 均为 pre-existing，与本次变更无关）
- [ ] 5.2 可选：对一个 Agent（如 macro_intelligence）的 Adapter 层改用 `generate_and_parse`（替代手动 generate + parse），验证重试能力端到端可用
