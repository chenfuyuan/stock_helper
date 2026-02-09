# 数据工程模块

`data_engineering` 模块负责金融市场数据的获取、处理和存储。它是所有分析和决策流程的基础层。

## 核心领域模型

### 股票 (`StockInfo`)
代表上市公司的基础信息。
- **属性**: 股票代码、名称、地域、行业、市场、上市日期、上市状态等。
- **源码**: `domain/model/stock.py`

### 日线行情 (`DailyBar`)
代表特定股票的每日交易数据。
- **属性**: 开盘价、最高价、最低价、收盘价、成交量、成交额。
- **源码**: `domain/model/daily_bar.py`

### 财务数据 (`FinancialReport` / `Finance`)
代表季度财务报表数据。
- **属性**: 营业收入、净利润、资产、负债等。
- **源码**: `domain/model/financial_report.py`

## 数据同步

数据同步通过 `application/commands` 目录中的 Command 类进行处理。这些命令协调以下各方之间的流转：
1.  **提供商 (Providers)**: 从外部 API（如 Tushare）获取原始数据。
2.  **存储库 (Repositories)**: 在数据库中保存/更新数据。

### 关键命令

- **`SyncStockListCmd`**: 获取最新的股票列表并更新 `stock_info` 表。
- **`SyncDailyBarCmd`**: 获取股票的每日价格数据。支持历史回补和每日增量更新。
- **`SyncFinanceCmd`**: 获取财务报表。

## 外部提供商

### Tushare
主要数据源为 Tushare。
- **实现**: `infrastructure/external_apis/tushare`
- **转换器 (Converters)**: 来自 Tushare 的数据在进入领域层之前，会使用转换器转换为领域实体。

## 持久化

数据使用 SQLAlchemy 模型存储在 PostgreSQL 中。
- **模型**: `infrastructure/persistence/models`
- **存储库**: `infrastructure/persistence/repositories`
