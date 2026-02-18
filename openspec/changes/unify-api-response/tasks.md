## 1. 准备工作

- [x] 1.1 备份当前代码状态，创建 git 分支
- [x] 1.2 确认测试环境可用，准备测试用例
- [x] 1.3 检查现有的 BaseResponse 和 ErrorResponse 定义

## 2. Coordinator 模块响应统一化

- [x] 2.1 修改 research_routes.py 中的 ResearchOrchestrationResponse 响应格式
- [x] 2.2 更新 /research 接口使用 BaseResponse[ResearchOrchestrationResponse]
- [x] 2.3 更新 /research/{session_id}/retry 接口使用 BaseResponse[ResearchOrchestrationResponse]
- [x] 2.4 更新 session_routes.py 中的响应格式
- [x] 2.5 验证 coordinator 模块所有接口响应格式正确性

## 3. LLM Platform 模块响应统一化

- [x] 3.1 修改 search_routes.py 中的 WebSearchApiResponse 响应格式
- [x] 3.2 更新 Web 搜索接口使用 BaseResponse[WebSearchApiResponse]
- [x] 3.3 修改 chat_routes.py 中的响应格式
- [x] 3.4 更新聊天接口使用 BaseResponse[ChatResponse]
- [x] 3.5 修改 config_routes.py 中的响应格式
- [x] 3.6 验证 llm_platform 模块所有接口响应格式正确性

## 4. Knowledge Center 模块响应统一化

- [x] 4.1 修改 graph_router.py 中的 StockNeighborResponse 响应格式
- [x] 4.2 更新 /stocks/{third_code}/neighbors 接口使用 BaseResponse[list[StockNeighborResponse]]
- [x] 4.3 更新 /stocks/{third_code}/graph 接口使用 BaseResponse[StockGraphResponse | None]
- [x] 4.4 更新 /sync 接口使用 BaseResponse[SyncGraphResponse]
- [x] 4.5 验证 knowledge_center 模块所有接口响应格式正确性

## 5. Research 模块响应统一化

- [x] 5.1 修改 technical_analyst_routes.py 中的响应格式
- [x] 5.2 修改 valuation_modeler_routes.py 中的响应格式
- [x] 5.3 修改 financial_auditor_routes.py 中的响应格式
- [x] 5.4 修改 catalyst_detective_routes.py 中的响应格式
- [x] 5.5 修改 macro_intelligence_routes.py 中的响应格式
- [x] 5.6 验证 research 模块所有接口响应格式正确性

## 6. Debate 模块响应统一化

- [x] 6.1 修改 debate_router.py 中的响应格式
- [x] 6.2 更新多头辩论接口使用 BaseResponse[BullAdvocateResult]
- [x] 6.3 更新空头辩论接口使用 BaseResponse[BearAdvocateResult]
- [x] 6.4 更新辩论裁决接口使用 BaseResponse[DebateResolutionResult]
- [x] 6.5 验证 debate 模块所有接口响应格式正确性

## 7. Judge 模块响应统一化

- [x] 7.1 修改 judge_router.py 中的响应格式
- [x] 7.2 更新投资裁决接口使用 BaseResponse[InvestmentVerdictResult]
- [x] 7.3 更新风险评估接口使用 BaseResponse[RiskAssessmentResult]
- [x] 7.4 验证 judge 模块所有接口响应格式正确性

## 8. Foundation 模块响应统一化

- [x] 8.1 修改 scheduler_routes.py 中的响应格式
- [x] 8.2 更新调度任务创建接口使用 BaseResponse[SchedulerTaskResult]
- [x] 8.3 更新调度任务查询接口使用 BaseResponse[SchedulerTaskInfo]
- [x] 8.4 更新调度任务执行接口使用 BaseResponse[SchedulerExecutionResult]
- [x] 8.5 验证 foundation 模块所有接口响应格式正确性

## 9. Market Insight 模块响应统一化

- [x] 9.1 修改 market_insight_router.py 中的响应格式
- [x] 9.2 更新市场趋势分析接口使用 BaseResponse[MarketTrendResult]
- [x] 9.3 更新板块轮动分析接口使用 BaseResponse[SectorRotationResult]
- [x] 9.4 更新市场情绪分析接口使用 BaseResponse[MarketSentimentResult]
- [x] 9.5 验证 market_insight 模块所有接口响应格式正确性

## 10. 错误处理统一化

- [x] 10.1 检查并更新错误处理中间件，确保统一返回 ErrorResponse
- [x] 10.2 验证所有异常情况都能正确转换为 ErrorResponse 格式
- [x] 10.3 测试各种错误场景的响应格式

## 11. 集成测试和验证

- [x] 11.1 运行所有模块的单元测试
- [x] 11.2 执行跨模块集成测试
- [x] 11.3 验证所有接口的响应格式符合规范
- [x] 11.4 检查 API 文档是否需要更新

## 12. 文档更新和收尾

- [x] 12.1 更新 API 文档，反映新的响应格式
- [x] 12.2 更新开发规范文档
- [x] 12.3 提交代码变更，创建合并请求
- [x] 12.4 部署到测试环境进行最终验证
