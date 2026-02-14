# Spec: module-config-isolation

模块配置隔离：全局 `Settings` 瘦身为仅含全局配置，data_engineering 和 llm_platform 各自在 `infrastructure/config.py` 中定义独立的 `BaseSettings` 子类管理模块专属配置（Tushare、同步引擎、LLM、Bocha 等），共用 `.env` 文件，跨模块不可见。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 全局配置瘦身

`src/shared/config.py` 的 `Settings` 类须仅包含真正的全局配置项（项目名称、API 前缀、运行环境、CORS、数据库连接），所有模块专属配置须从中移除。

#### Scenario: shared config 不含模块配置

- **WHEN** 审查 `src/shared/config.py`
- **THEN** `Settings` 类中不存在 `TUSHARE_*`、`SYNC_*`、`LLM_*`、`BOCHA_*` 等模块专属配置项

### Requirement: data_engineering 模块配置独立

`data_engineering` 模块须在 `infrastructure/config.py` 中定义独立的 `DataEngineeringConfig(BaseSettings)` 类，包含 Tushare 和同步引擎相关配置，并暴露模块级单例 `de_config`。

#### Scenario: Tushare 配置归属 data_engineering

- **WHEN** data_engineering 模块需要读取 `TUSHARE_TOKEN` 或 `TUSHARE_MIN_INTERVAL`
- **THEN** 通过 `de_config.TUSHARE_TOKEN` 读取（`de_config` 为 `DataEngineeringConfig` 实例），不通过 `settings.TUSHARE_TOKEN`

#### Scenario: 同步配置归属 data_engineering

- **WHEN** 同步引擎需要读取 `SYNC_DAILY_HISTORY_BATCH_SIZE` 等配置
- **THEN** 通过 `de_config.SYNC_DAILY_HISTORY_BATCH_SIZE` 读取，不通过 `settings`

### Requirement: llm_platform 模块配置独立

`llm_platform` 模块须在 `infrastructure/config.py` 中定义独立的 `LLMPlatformConfig(BaseSettings)` 类，包含 LLM 和 Web Search 相关配置，并暴露模块级单例 `llm_config`。

#### Scenario: LLM 配置归属 llm_platform

- **WHEN** llm_platform 模块需要读取 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`
- **THEN** 通过 `llm_config.LLM_API_KEY` 读取，不通过 `settings`

#### Scenario: Bocha 配置归属 llm_platform

- **WHEN** Web Search 功能需要读取 `BOCHA_API_KEY`、`BOCHA_BASE_URL`
- **THEN** 通过 `llm_config.BOCHA_API_KEY` 读取，不通过 `settings`

### Requirement: 环境变量兼容性

模块级 Config 须与全局 Config 共用同一个 `.env` 文件，迁移后不要求用户修改环境变量名称。

#### Scenario: .env 文件无需变更

- **WHEN** 将模块配置从 `shared/config.py` 迁移到各模块 `infrastructure/config.py`
- **THEN** `.env` 文件中的环境变量名称保持不变（如 `TUSHARE_TOKEN` 仍为 `TUSHARE_TOKEN`），各模块的 `BaseSettings` 自动从同一个 `.env` 加载

### Requirement: 配置跨模块不可见

模块的配置实例仅在自身模块内部可访问，其他模块不可直接 import 或读取。

#### Scenario: Research 无法读取 Tushare 配置

- **WHEN** Research 模块代码中尝试 `from src.modules.data_engineering.infrastructure.config import de_config`
- **THEN** 此 import 违反跨模块依赖规范（Research 不应依赖 data_engineering 的 Infrastructure 层），代码审查须拒绝
