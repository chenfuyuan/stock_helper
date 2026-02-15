# Market Insight 模块调用指南

## 模块概述

**Market Insight** 是 Stock Helper 系统的板块洞察分析模块，提供以下核心能力：

- **概念热度计算**：基于等权平均法聚合概念成分股涨跌幅，输出板块热度排名
- **涨停扫描归因**：识别当日涨停个股，将涨停股映射至所属概念板块
- **每日复盘报告**：自动生成包含强势概念、涨停天梯、市场概览的 Markdown 日报

**定位**：支撑能力层模块（Supporting Domain），为决策层提供板块维度的市场洞察数据。

**依赖关系**：
- 上游：依赖 `data_engineering` 模块提供概念数据和日线行情数据
- 下游：为 Research、Judge 等业务核心层模块提供板块分析能力

---

## 前置条件

### 1. 数据同步

Market Insight 依赖以下数据：

- **概念板块数据**：通过 `data_engineering` 模块同步（使用 AkShare 数据源）
- **日线行情数据**：通过 `data_engineering` 模块同步（使用 TuShare 数据源）

确保在执行复盘分析前，已完成相应日期的数据同步。

### 2. 数据库 Migration

执行以下命令运行数据库迁移，创建 Market Insight 相关表：

```bash
alembic upgrade head
```

这将创建：
- `mi_concept_heat`：概念热度数据表
- `mi_limit_up_stock`：涨停股数据表

---

## CLI 用法

### 生成每日复盘报告

```bash
python -m src.modules.market_insight.presentation.cli.daily_review_cli --date 2025-01-06 --output-dir reports
```

**参数说明**：
- `--date`：交易日期（格式：YYYY-MM-DD），默认为今天
- `--output-dir`：报告输出目录，默认为 `reports`

**执行流程**：
1. 从 `data_engineering` 获取指定日期的全市场日线数据
2. 从 `data_engineering` 获取概念板块及成分股映射
3. 计算概念板块热度（等权平均涨跌幅）
4. 扫描涨停股并归因至概念
5. 将计算结果持久化至 PostgreSQL
6. 生成 Markdown 复盘报告

**输出示例**：
```
2025-01-06 10:30:15 - __main__ - INFO - 开始生成每日复盘报告: 2025-01-06
2025-01-06 10:30:20 - __main__ - INFO - 每日复盘报告生成完成:
  交易日期: 2025-01-06
  概念数量: 320
  涨停数量: 45
  报告路径: reports/2025-01-06-market-insight.md
  耗时: 5.23秒
```

---

## HTTP API 说明

Market Insight 提供以下 REST API 端点，基于 FastAPI 实现。

### 1. 查询概念热度

**端点**：`GET /api/market-insight/concept-heat`

**查询参数**：
- `trade_date`（必填）：交易日期，格式 YYYY-MM-DD
- `top_n`（可选）：返回前 N 名概念，默认 10

**响应示例**：
```json
[
  {
    "trade_date": "2025-01-06",
    "concept_code": "BK0493",
    "concept_name": "低空经济",
    "avg_pct_chg": 5.5,
    "stock_count": 50,
    "up_count": 45,
    "down_count": 5,
    "limit_up_count": 10,
    "total_amount": 5000000000.0
  }
]
```

**curl 示例**：
```bash
curl -X GET "http://localhost:8000/api/market-insight/concept-heat?trade_date=2025-01-06&top_n=10"
```

---

### 2. 查询涨停股

**端点**：`GET /api/market-insight/limit-up`

**查询参数**：
- `trade_date`（必填）：交易日期，格式 YYYY-MM-DD
- `concept_code`（可选）：概念代码，用于过滤特定概念下的涨停股

**响应示例**：
```json
[
  {
    "trade_date": "2025-01-06",
    "third_code": "000001.SZ",
    "stock_name": "平安银行",
    "pct_chg": 10.01,
    "close": 12.0,
    "amount": 200000000.0,
    "concept_codes": ["BK0001", "BK0002"],
    "concept_names": ["金融概念", "深圳本地"],
    "limit_type": "MAIN_BOARD"
  }
]
```

**curl 示例**：
```bash
# 查询全部涨停股
curl -X GET "http://localhost:8000/api/market-insight/limit-up?trade_date=2025-01-06"

# 按概念过滤
curl -X GET "http://localhost:8000/api/market-insight/limit-up?trade_date=2025-01-06&concept_code=BK0493"
```

---

### 3. 触发每日复盘报告生成

**端点**：`POST /api/market-insight/daily-report`

**查询参数**：
- `trade_date`（必填）：交易日期，格式 YYYY-MM-DD

**响应示例**：
```json
{
  "trade_date": "2025-01-06",
  "concept_count": 320,
  "limit_up_count": 45,
  "report_path": "reports/2025-01-06-market-insight.md",
  "elapsed_seconds": 5.23
}
```

**curl 示例**：
```bash
curl -X POST "http://localhost:8000/api/market-insight/daily-report?trade_date=2025-01-06"
```

---

## 输出说明

### Markdown 报告结构

生成的复盘报告位于 `{output_dir}/YYYY-MM-DD-market-insight.md`，包含以下章节：

#### 1. 标题
```markdown
# 每日市场洞察 - 2025-01-06
```

#### 2. Top N 强势概念
按平均涨跌幅降序，展示前 N 个概念：

| 排名 | 概念名称 | 涨跌幅(%) | 涨停家数 | 成交额(亿) |
|------|---------|----------|---------|-----------|
| 1 | 低空经济 | 5.50 | 10 | 50.00 |

#### 3. 今日涨停天梯
按概念分组展示涨停股：

```markdown
### 低空经济
- **中信海直** (000099.SZ) +10.01%
- **万丰奥威** (002085.SZ) +10.00%
```

#### 4. 市场概览
统计数据：
- 涨停总数
- 概念板块总数

#### 5. 数据更新时间
报告生成时间戳

---

## 常见问题

### 1. 执行报告生成时提示"无行情数据"

**原因**：指定日期为非交易日，或该日期的日线数据尚未同步。

**解决方案**：
- 确认指定日期为交易日
- 执行 `data_engineering` 模块的日线同步任务

---

### 2. 概念热度数据为空

**原因**：概念板块数据未同步，或所有概念成分股当日全部停牌。

**解决方案**：
- 执行概念数据同步：
  ```bash
  # 通过 data_engineering 模块同步概念数据
  ```
- 检查日线数据是否正常

---

### 3. 涨停股识别不准确

**说明**：MVP 版本使用涨跌幅阈值法判断涨停，对于新股首日、复牌股等特殊情况可能存在误判。

**阈值规则**：
- 主板/中小板：≥ 9.9%
- 创业板/科创板：≥ 19.8%
- ST 股票：≥ 4.9%
- 北交所：≥ 29.5%

**后续优化**：可切换为精确涨停价计算或接入专用数据源。

---

### 4. 如何定时执行每日复盘

可使用系统 cron 或任务调度工具：

```bash
# crontab 示例：每个交易日收盘后 16:00 执行
0 16 * * 1-5 cd /path/to/stock_helper && python -m src.modules.market_insight.presentation.cli.daily_review_cli
```

---

## 性能说明

- **数据量**：单日全市场约 5000 只股票 × 300+ 概念板块
- **计算耗时**：通常在 5-10 秒内完成（取决于数据库查询性能）
- **并发支持**：Repository 层使用 UPSERT 策略，支持幂等重复执行

---

## 技术栈

- **框架**：FastAPI (REST API)、Pydantic (DTO 校验)
- **数据库**：PostgreSQL (JSONB 支持)
- **ORM**：SQLAlchemy 2.0 (AsyncSession)
- **迁移工具**：Alembic
- **架构模式**：DDD (领域驱动设计)、Clean Architecture

---

## 相关文档

- [架构设计](../../openspec/changes/market-insight-mvp/design.md)
- [Spec 规范](../../openspec/changes/market-insight-mvp/specs/)
- [模块注册表](../../openspec/specs/vision-and-modules.md)
