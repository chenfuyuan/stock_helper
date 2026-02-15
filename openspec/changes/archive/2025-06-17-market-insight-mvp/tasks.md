## 1. data_engineering 扩展（前置依赖）

- [x] 1.1 在 `IMarketQuoteRepository` 新增 `get_all_by_trade_date(trade_date: date) -> list[StockDaily]` 方法
- [x] 1.2 在 `StockDailyRepositoryImpl` 中实现 `get_all_by_trade_date` 查询逻辑
- [x] 1.3 新增 `GetDailyBarsByDateUseCase`（`data_engineering/application/queries/get_daily_bars_by_date.py`）
- [x] 1.4 在 `DataEngineeringContainer` 中注册并暴露 `GetDailyBarsByDateUseCase`
- [x] 1.5 为 `GetDailyBarsByDateUseCase` 编写单元测试

## 2. 模块骨架搭建

- [x] 2.1 创建 `src/modules/market_insight/` 目录结构（application/commands/、application/queries/、application/dtos/、domain/model/、domain/ports/repositories/、domain/dtos/、domain/services/、infrastructure/adapters/、infrastructure/persistence/models/、infrastructure/persistence/repositories/、infrastructure/report/、presentation/rest/、presentation/cli/）
- [x] 2.2 添加各级 `__init__.py` 文件
- [x] 2.3 创建 `market_insight/domain/exceptions.py`（模块领域异常，继承 `AppException`）

## 3. Domain 层 — 模型与枚举

- [x] 3.1 实现 `LimitType` 枚举（`domain/model/enums.py`）：MAIN_BOARD、GEM、STAR、BSE、ST
- [x] 3.2 实现 `ConceptHeat` 实体（`domain/model/concept_heat.py`）：trade_date、concept_code、concept_name、avg_pct_chg、stock_count、up_count、down_count、limit_up_count、total_amount
- [x] 3.3 实现 `LimitUpStock` 实体（`domain/model/limit_up_stock.py`）：trade_date、third_code、stock_name、pct_chg、close、amount、concepts（Concept 对象列表）、limit_type

## 4. Domain 层 — DTO 定义

- [x] 4.1 实现领域层 DTO（`domain/dtos/insight_dtos.py`）：ConceptWithStocksDTO、ConceptStockDTO、StockDailyDTO、ConceptInfoDTO

## 5. Domain 层 — Port 接口

- [x] 5.1 实现 `IConceptDataPort` ABC（`domain/ports/concept_data_port.py`）
- [x] 5.2 实现 `IMarketDataPort` ABC（`domain/ports/market_data_port.py`）
- [x] 5.3 实现 `IConceptHeatRepository` ABC（`domain/ports/repositories/concept_heat_repo.py`）
- [x] 5.4 实现 `ILimitUpRepository` ABC（`domain/ports/repositories/limit_up_repo.py`）

## 6. Domain 层 — 领域服务

- [x] 6.1 实现 `ConceptHeatCalculator`（`domain/services/concept_heat_calculator.py`）：等权平均计算、涨停统计、停牌过滤、全停牌排除
- [x] 6.2 为 `ConceptHeatCalculator` 编写单元测试（正常计算、全停牌、涨停统计）
- [x] 6.3 实现 `LimitUpScanner`（`domain/services/limit_up_scanner.py`）：阈值判定（主板/创业板/科创板/北交所/ST）、概念归因映射
- [x] 6.4 为 `LimitUpScanner` 编写单元测试（各板块涨停识别、未达阈值、概念归因、无概念归属）

## 7. Infrastructure 层 — Adapters

- [x] 7.1 实现 `DeConceptDataAdapter`（`infrastructure/adapters/de_concept_data_adapter.py`）：调用 DE 的 IConceptRepository，转换为 MI 的 DTO
- [x] 7.2 实现 `DeMarketDataAdapter`（`infrastructure/adapters/de_market_data_adapter.py`）：调用 DE 的 GetDailyBarsByDateUseCase，转换为 MI 的 DTO

## 8. Infrastructure 层 — 持久化

- [x] 8.1 实现 `ConceptHeatModel` ORM（`infrastructure/persistence/models/concept_heat_model.py`）：映射 `mi_concept_heat` 表
- [x] 8.2 实现 `LimitUpStockModel` ORM（`infrastructure/persistence/models/limit_up_stock_model.py`）：映射 `mi_limit_up_stock` 表
- [x] 8.3 创建 Alembic Migration：`mi_concept_heat` 表（含 (trade_date, concept_code) 唯一约束）
- [x] 8.4 创建 Alembic Migration：`mi_limit_up_stock` 表（含 (trade_date, third_code) 唯一约束，concepts 用 JSONB 存储对象数组）
- [x] 8.5 实现 `PgConceptHeatRepository`（`infrastructure/persistence/repositories/pg_concept_heat_repo.py`）：save_all（UPSERT）、get_by_date、get_by_concept_and_date_range
- [x] 8.6 实现 `PgLimitUpRepository`（`infrastructure/persistence/repositories/pg_limit_up_repo.py`）：save_all（UPSERT）、get_by_date、get_by_date_and_concept（JSONB 查询）

## 9. Infrastructure 层 — 报告生成

- [x] 9.1 实现 `MarkdownReportGenerator`（`infrastructure/report/markdown_report_generator.py`）：生成含标题、Top N 强势概念表格、涨停天梯、市场概览、数据更新时间的 Markdown 文件
- [x] 9.2 为 `MarkdownReportGenerator` 编写单元测试（正常报告、无涨停场景、文件覆盖）

## 10. Application 层 — 命令与查询

- [x] 10.1 实现 Application 层 DTO（`application/dtos/market_insight_dtos.py`）：ConceptHeatDTO、LimitUpStockDTO、DailyReportResult
- [x] 10.2 实现 `GenerateDailyReportCmd`（`application/commands/generate_daily_report_cmd.py`）：编排完整流程（获取数据 → 构建索引 → 计算热度 → 扫描涨停 → 持久化 → 生成报告）
- [x] 10.3 实现 `GetConceptHeatQuery`（`application/queries/get_concept_heat_query.py`）
- [x] 10.4 实现 `GetLimitUpQuery`（`application/queries/get_limit_up_query.py`）

## 11. Presentation 层

- [x] 11.1 实现 `MarketInsightRouter`（`presentation/rest/market_insight_router.py`）：GET /concept-heat、GET /limit-up、POST /daily-report
- [x] 11.2 将 `MarketInsightRouter` 注册到 FastAPI app（主路由入口）
- [x] 11.3 实现 CLI 入口（`presentation/cli/daily_review_cli.py`）

## 12. DI 容器

- [x] 12.1 实现 `MarketInsightContainer`（`container.py`）：组装全部依赖（Adapters、Repositories、Services、Commands、Queries）

## 13. 架构文档与调用指南

- [x] 13.1 更新 `openspec/specs/vision-and-modules.md`：在模块注册表 4.2 节新增 market_insight 条目，在上下文映射中补充依赖关系
- [x] 13.2 编写 `docs/guides/market-insight-guide.md`：模块概述、前置条件、CLI 用法、HTTP API 说明（含 curl 示例）、输出说明、常见问题

## 14. 集成测试与验证

- [x] 14.1 为 `GenerateDailyReportCmd` 编写集成测试（mock DE 数据，验证完整流程：计算 → 持久化 → 报告生成）
- [x] 14.2 为 REST API 端点编写集成测试（GET/POST 请求验证、参数校验、空数据场景）
- [x] 14.3 运行全量测试确认无回归
