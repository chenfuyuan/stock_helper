## 1. 配置模块化（Phase 1）

- [ ] 1.1 创建 `src/modules/data_engineering/infrastructure/config.py`，定义 `DataEngineeringConfig(BaseSettings)` 类，包含 `TUSHARE_TOKEN`、`TUSHARE_MIN_INTERVAL`、`SYNC_DAILY_HISTORY_BATCH_SIZE`、`SYNC_FINANCE_HISTORY_BATCH_SIZE`、`SYNC_FINANCE_HISTORY_START_DATE`、`SYNC_INCREMENTAL_MISSING_LIMIT`、`SYNC_FAILURE_MAX_RETRIES`，暴露 `de_config` 单例
- [ ] 1.2 创建 `src/modules/llm_platform/infrastructure/config.py`，定义 `LLMPlatformConfig(BaseSettings)` 类，包含 `LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`BOCHA_API_KEY`、`BOCHA_BASE_URL`，暴露 `llm_config` 单例
- [ ] 1.3 瘦身 `src/shared/config.py`：移除上述模块专属配置项，仅保留 `PROJECT_NAME`、`API_V1_STR`、`ENVIRONMENT`、`BACKEND_CORS_ORIGINS`、`POSTGRES_*`、`SQLALCHEMY_DATABASE_URI`
- [ ] 1.4 全局 `grep` 替换：将所有 `settings.TUSHARE_*` → `de_config.TUSHARE_*`，`settings.SYNC_*` → `de_config.SYNC_*`，`settings.LLM_*` → `llm_config.LLM_*`，`settings.BOCHA_*` → `llm_config.BOCHA_*`，更新对应 import
- [ ] 1.5 验证：`docker compose exec app python -c "from src.shared.config import settings; from src.modules.data_engineering.infrastructure.config import de_config; from src.modules.llm_platform.infrastructure.config import llm_config"` 正常执行

## 2. Composition Root 引入（Phase 1）

- [ ] 2.1 创建 `src/modules/data_engineering/container.py`，定义 `DataEngineeringContainer` 类，封装 `get_daily_bars_use_case()`、`get_finance_use_case()`、`get_stock_basic_info_use_case()` 等 UseCase 的组装逻辑
- [ ] 2.2 创建 `src/modules/llm_platform/container.py`，定义 `LLMPlatformContainer` 类，封装 `llm_service()`、`llm_registry()` 等的组装逻辑
- [ ] 2.3 创建 `src/modules/research/container.py`，定义 `ResearchContainer` 类，封装 `technical_analyst_service()`、`financial_auditor_service()`、`valuation_modeler_service()` 的组装逻辑（内部通过 `DataEngineeringContainer` 和 `LLMPlatformContainer` 获取跨模块依赖）
- [ ] 2.4 提取 `main.py` 的 LLM Registry 初始化逻辑到 `src/modules/llm_platform/application/services/startup.py`（`LLMPlatformStartup.initialize()`），`main.py` 改为调用该方法
- [ ] 2.5 验证：`docker compose exec app python -c "import src.main"` 正常启动，无 Infrastructure 直接 import

## 3. 依赖方向修复与路由模块自治（Phase 2）

- [ ] 3.1 重构 `research/presentation/rest/technical_analyst_routes.py`：移除所有手写工厂函数（约 8 个），改用 `ResearchContainer(session).technical_analyst_service()` 一行获取 Service
- [ ] 3.2 重构 `research/presentation/rest/financial_auditor_routes.py`：同上，移除工厂函数，改用 Container
- [ ] 3.3 重构 `research/presentation/rest/valuation_modeler_routes.py`：同上
- [ ] 3.4 验证：`grep -r "data_engineering.infrastructure" src/modules/research/` 返回空（无跨模块 Infrastructure 依赖）
- [ ] 3.5 创建 `src/modules/research/presentation/rest/__init__.py`，导出统一 `router`（合并 technical_analyst、financial_auditor、valuation_modeler 三个子路由）
- [ ] 3.6 创建 `src/modules/data_engineering/presentation/rest/__init__.py`，导出统一 `router`（合并 stock_routes、scheduler_routes）
- [ ] 3.7 创建 `src/modules/llm_platform/presentation/rest/__init__.py`，导出统一 `router`（合并 config_routes、chat_routes、search_routes）
- [ ] 3.8 简化 `src/api/routes.py`：改为仅 include 模块级 router（约 3-4 行），不再引用模块内部子路由
- [ ] 3.9 验证：所有 API 端点功能不变（手动测试或运行已有测试）

## 4. DTO 目录重组（Phase 3）

- [ ] 4.1 创建 `src/modules/research/domain/dtos/` 子包（含 `__init__.py`）
- [ ] 4.2 迁移 `research/domain/ports/dto_inputs.py` → `research/domain/dtos/daily_bar_input.py`
- [ ] 4.3 拆分 `research/domain/ports/dto_financial_inputs.py`：`FinanceRecordInput` → `research/domain/dtos/financial_record_input.py`，`FinancialSnapshotDTO` → `research/domain/dtos/financial_snapshot.py`
- [ ] 4.4 拆分 `research/domain/ports/dto_valuation_inputs.py`：`StockOverviewInput`/`ValuationDailyInput` → `research/domain/dtos/valuation_inputs.py`，`ValuationSnapshotDTO` → `research/domain/dtos/valuation_snapshot.py`
- [ ] 4.5 提取 `PlaceholderValue` 到 `research/domain/dtos/types.py`，统一为 `Union[float, int, str, list[float], list[int], list[str]]`
- [ ] 4.6 删除 `research/domain/ports/` 下的原 DTO 文件（确认无残留 import 后）
- [ ] 4.7 迁移 `research/domain/dtos.py` → `research/domain/dtos/technical_analysis_dtos.py`
- [ ] 4.8 移动 `research/domain/financial_dtos.py`、`valuation_dtos.py`、`indicators_snapshot.py` 到 `research/domain/dtos/` 下
- [ ] 4.9 全局更新所有引用上述文件的 import 路径

## 5. 文件命名与目录归位（Phase 3）

- [ ] 5.1 重命名 `data_engineering/domain/model/daily_bar.py` → `stock_daily.py`，全局更新 import
- [ ] 5.2 移动 `data_engineering/application/commands/get_stock_basic_info.py` → `application/queries/get_stock_basic_info.py`，全局更新 import
- [ ] 5.3 迁移 `research/agents/` 残留内容（如 Prompt 模板）到 `research/infrastructure/agents/`，更新路径引用
- [ ] 5.4 全局 `grep` 验证：所有旧路径（`ports/dto_inputs`、`ports/dto_financial_inputs`、`ports/dto_valuation_inputs`、`domain/dtos.py`、`model/daily_bar`、`commands/get_stock_basic_info`）不再出现在源码中

## 6. 最终验证

- [ ] 6.1 `docker compose exec app python -c "import src.main"` 正常启动
- [ ] 6.2 `grep -rn "data_engineering.infrastructure" src/modules/research/` 返回空
- [ ] 6.3 `grep -rn "settings.TUSHARE\|settings.SYNC_\|settings.LLM_\|settings.BOCHA_" src/` 返回空（仅 shared config 中无此类引用）
- [ ] 6.4 各 API 端点手动测试通过（技术分析、财务审计、估值建模）
- [ ] 6.5 现有自动化测试（如有）全部通过
