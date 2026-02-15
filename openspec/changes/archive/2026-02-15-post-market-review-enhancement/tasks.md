## 1. 环境准备

- [x] 1.1 项目依赖中添加 `akshare`（pip / requirements.txt / pyproject.toml）

## 2. DE 领域层：DTO、Port、实体定义

> 类型定义阶段，无需测试。为后续 TDD 提供类型基础。

- [x] 2.1 创建 `domain/dtos/market_sentiment_dtos.py`（`LimitUpPoolDTO`、`BrokenBoardDTO`、`PreviousLimitUpDTO`）
- [x] 2.2 创建 `domain/dtos/dragon_tiger_dtos.py`（`DragonTigerDetailDTO`）
- [x] 2.3 创建 `domain/dtos/capital_flow_dtos.py`（`SectorCapitalFlowDTO`）
- [x] 2.4 创建 `domain/ports/providers/market_sentiment_provider.py`（`IMarketSentimentProvider` ABC）
- [x] 2.5 创建 `domain/ports/providers/dragon_tiger_provider.py`（`IDragonTigerProvider` ABC）
- [x] 2.6 创建 `domain/ports/providers/sector_capital_flow_provider.py`（`ISectorCapitalFlowProvider` ABC）
- [x] 2.7 创建领域实体：`LimitUpPoolStock`、`BrokenBoardStock`、`PreviousLimitUpStock`、`DragonTigerDetail`、`SectorCapitalFlow`
- [x] 2.8 创建 Repository Port：`ILimitUpPoolRepository`、`IBrokenBoardRepository`、`IPreviousLimitUpRepository`、`IDragonTigerRepository`、`ISectorCapitalFlowRepository`
- [x] 2.9 扩展 `domain/model/enums.py` 的 `SyncJobType` 枚举，新增 `AKSHARE_MARKET_DATA`

## 3. DE 基础设施：AkShare 客户端（Test-After）

- [x] 3.1 提取 `AkShareBaseClient` 基类到 `base_client.py`（限速锁 + `_run_in_executor` + `_rate_limited_call`）
- [x] 3.2 重构 `AkShareConceptClient` 继承 `AkShareBaseClient`，移除重复代码
- [x] 3.3 实现 `AkShareMarketDataClient`（继承 `AkShareBaseClient`，实现三个 Provider 接口）
- [x] 3.4 编写 `AkShareMarketDataClient` 单元测试（mock akshare API，验证各 `fetch_*` 方法：正常返回、空数据、异常处理）

## 4. DE 持久化层：ORM、Migration、Repository（Test-After）

- [x] 4.1 创建 ORM 模型：`LimitUpPoolModel`、`BrokenBoardModel`、`PreviousLimitUpModel`、`DragonTigerModel`（JSONB 字段）、`SectorCapitalFlowModel`
- [x] 4.2 创建 Alembic migration：生成 5 张新表，含唯一约束
- [x] 4.3 实现 `PgLimitUpPoolRepository`（UPSERT on `trade_date + third_code`）
- [x] 4.4 实现 `PgBrokenBoardRepository`（UPSERT on `trade_date + third_code`）
- [x] 4.5 实现 `PgPreviousLimitUpRepository`（UPSERT on `trade_date + third_code`）
- [x] 4.6 实现 `PgDragonTigerRepository`（UPSERT on `trade_date + third_code + reason`）
- [x] 4.7 实现 `PgSectorCapitalFlowRepository`（UPSERT on `trade_date + sector_name + sector_type`）
- [x] 4.8 编写各 Repository 集成测试（UPSERT 幂等性、按日期查询、唯一约束验证）

## 5. DE 应用层：同步命令与查询

- [x] 🔴 5.1 编写 `SyncAkShareMarketDataCmd` 单元测试（mock 全部 Provider + Repository，验证：正常全量同步、部分失败异常隔离、幂等行为）
- [x] 5.2 实现 `SyncAkShareMarketDataCmd`（通过上述测试）
- [x] 5.3 实现查询用例：`GetLimitUpPoolByDateUseCase`、`GetBrokenBoardByDateUseCase`、`GetPreviousLimitUpByDateUseCase`、`GetDragonTigerByDateUseCase`、`GetSectorCapitalFlowByDateUseCase`
- [x] 5.4 更新 `DataEngineeringContainer`：注册所有新增 Provider、Repository、Command、Query

## 6. MI 领域层：DTO 与 Port 定义

> 类型定义阶段，无需测试。为后续 TDD 提供类型基础。

- [x] 6.1 创建 `domain/dtos/sentiment_dtos.py`（MI 领域层 DTO：`LimitUpPoolItemDTO` 等输入 DTO + `ConsecutiveBoardLadder`、`BoardTier`、`PreviousLimitUpPerformance`、`BrokenBoardAnalysis` 等输出 DTO）
- [x] 6.2 创建 `domain/dtos/capital_flow_dtos.py`（MI 领域层 DTO：`DragonTigerItemDTO`、`SectorCapitalFlowItemDTO` 等输入 DTO + `DragonTigerAnalysis`、`DragonTigerStockSummary`、`SectorCapitalFlowAnalysis` 等输出 DTO）
- [x] 6.3 创建 `domain/ports/sentiment_data_port.py`（`ISentimentDataPort` ABC）
- [x] 6.4 创建 `domain/ports/capital_flow_data_port.py`（`ICapitalFlowDataPort` ABC）

## 7. MI 领域服务（Test-First ★）

> 纯函数式领域服务，TDD 最佳场景。先 Red 再 Green 再 Refactor。

- [x] 🔴 7.1 编写 `SentimentAnalyzer` 全部测试用例（基于 spec scenarios：连板梯队分布、涨停池为空、昨日涨停赚钱效应、昨日涨停为空、炸板率计算、无炸板；含边界条件）
- [x] 7.2 实现 `SentimentAnalyzer`（通过上述测试）
- [x] 🔴 7.3 编写 `CapitalFlowAnalyzer` 全部测试用例（基于 spec scenarios：龙虎榜分析正常、机构席位识别、龙虎榜为空、板块资金流向排名、资金流向为空）
- [x] 7.4 实现 `CapitalFlowAnalyzer`（通过上述测试）

## 8. MI 基础设施：适配器（Test-After）

- [x] 8.1 实现 `DeSentimentDataAdapter`（桥接 DE 查询用例，转换 DTO）
- [x] 8.2 实现 `DeCapitalFlowDataAdapter`（桥接 DE 查询用例，转换 DTO）

## 9. MI 应用层：查询用例与命令扩展（Test-First ★）

- [x] 9.1 创建 `application/dtos/sentiment_metrics_dtos.py`（`SentimentMetricsDTO`）
- [x] 9.2 创建 `application/dtos/capital_flow_analysis_dtos.py`（`CapitalFlowAnalysisDTO`）
- [x] 🔴 9.3 编写 `GenerateDailyReportCmd` 扩展测试（mock 新增 Port + 领域服务，验证：完整流程含情绪与资金、情绪数据失败不中断、资金数据失败不中断、DailyReportResult 新增字段）
- [x] 9.4 修改 `GenerateDailyReportCmd`：注入新依赖，新增步骤 8-11（异常隔离），扩展 `DailyReportResult`（通过上述测试）
- [x] 9.5 实现 `GetSentimentMetricsQuery` 和 `GetCapitalFlowAnalysisQuery`

## 10. MI 报告与 API 扩展

- [x] 🔴 10.1 编写 `MarkdownReportGenerator` 扩展测试（验证：完整报告含 7 个章节、情绪数据不可用显示提示、资金数据不可用显示提示）
- [x] 10.2 修改 `MarkdownReportGenerator`：新增"市场情绪"和"资金动向"章节（通过上述测试）
- [x] 10.3 修改 `market_insight_router.py`：新增 `/sentiment-metrics` 和 `/capital-flow` GET 端点
- [x] 10.4 编写新增 REST API 端点集成测试
- [x] 10.5 更新 `MarketInsightContainer`：注册新增 Adapter、领域服务、查询用例
