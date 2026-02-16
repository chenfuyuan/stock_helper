# HTTP 调用指南

本文档提供了项目中所有 HTTP API 的详细调用指导。

## Health Check

### GET /health

**功能描述**

健康检查端点，用于检查应用状态及数据库连接。

**curl 命令**

```bash
curl -X GET http://localhost:8000/api/v1/health
```

**入参**

无

---

## Data Engineering

### POST /sync

**功能描述**

同步股票基础列表。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/stocks/sync
```

**入参**

无

### POST /sync/daily/incremental

**功能描述**

增量同步股票日线历史数据（日常操作）。用于定期同步最新数据，支持分页处理避免超时。可指定股票代码同步单只股票，不指定则按分页同步多只股票。

**curl 命令**

```bash
# 同步多只股票（分页）
curl -X POST "http://localhost:8000/api/v1/stocks/sync/daily/incremental?limit=10&offset=0"

# 同步指定股票
curl -X POST "http://localhost:8000/api/v1/stocks/sync/daily/incremental?symbol=000001"
```

**入参**

*   `limit` (integer, query, optional, default: 10): 限制同步的股票数量（仅在未指定 symbol 时有效）。
*   `offset` (integer, query, optional, default: 0): 同步的起始偏移量（仅在未指定 symbol 时有效）。
*   `symbol` (string, query, optional): 指定股票代码进行单只股票同步。

### POST /sync/daily/full

**功能描述**

日线历史全量同步（管理操作）。用于初始化或数据修复，一次性同步所有历史数据，使用 SyncEngine 自动分批处理，适合低频手动触发。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/stocks/sync/daily/full
```

**入参**

无

### POST /sync/finance/full

**功能描述**

财务历史全量同步（管理操作）。用于初始化或数据修复，一次性同步所有财务历史数据，使用 SyncEngine 自动分批处理，适合低频手动触发。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/stocks/sync/finance/full
```

**入参**

无

---

## Scheduler

### GET /scheduler/status

**功能描述**

获取当前调度器的运行状态以及已注册的任务列表。

**curl 命令**

```bash
curl -X GET http://localhost:8000/api/v1/scheduler/status
```

**入参**

无

### POST /scheduler/jobs/schedule

**功能描述**

调度新任务或更新已有任务的调度计划。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/jobs/schedule -H "Content-Type: application/json" -d '{
  "job_id": "some_job",
  "job_name": "Some Job",
  "cron_expression": "0 0 * * *",
  "timezone": "Asia/Shanghai",
  "job_kwargs": {}
}'
```

**入参** (Request Body)

*   `job_id` (string, required): 任务的唯一ID。
*   `job_name` (string, optional): 任务的可读名称。
*   `cron_expression` (string, required): CRON表达式。
*   `timezone` (string, optional, default: 'Asia/Shanghai'): 时区。
*   `job_kwargs` (object, optional): 传递给任务的参数。

### POST /scheduler/jobs/{job_id}/start

**功能描述**

启动指定任务（等同于 schedule_job）。

**curl 命令**

```bash
curl -X POST "http://localhost:8000/api/v1/scheduler/jobs/some_job/start?cron_expression=0%200%20*%20*%20*&timezone=Asia/Shanghai"
```

**入参**

*   `job_id` (string, path, required): 任务的唯一ID。
*   `cron_expression` (string, query, required): CRON表达式。
*   `timezone` (string, query, optional, default: 'Asia/Shanghai'): 时区。

### POST /scheduler/jobs/{job_id}/stop

**功能描述**

停止指定任务并标记为禁用。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/jobs/some_job/stop
```

**入参**

*   `job_id` (string, path, required): 任务的唯一ID。

### POST /scheduler/jobs/{job_id}/trigger

**功能描述**

立即触发指定任务执行一次。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/jobs/some_job/trigger
```

**入参**

*   `job_id` (string, path, required): 任务的唯一ID。

### GET /scheduler/executions

**功能描述**

查询调度执行历史记录。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/scheduler/executions?job_id=some_job&limit=20"
```

**入参**

*   `job_id` (string, query, optional): 按任务ID过滤。
*   `limit` (integer, query, optional, default: 20): 返回记录的数量。

---

## Market Insight

### GET /market-insight/concept-heat

**功能描述**

获取指定交易日的概念热度排名。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/market-insight/concept-heat?trade_date=2023-01-01&top_n=10"
```

**入参**

*   `trade_date` (date, query, required): 交易日期。
*   `top_n` (integer, query, optional, default: 10): 返回前 N 名概念。

### GET /market-insight/limit-up

**功能描述**

获取指定交易日的涨停股列表，支持按概念过滤。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/market-insight/limit-up?trade_date=2023-01-01&concept_code=C001"
```

**入参**

*   `trade_date` (date, query, required): 交易日期。
*   `concept_code` (string, query, optional): 概念代码，用于过滤。

### POST /market-insight/daily-report

**功能描述**

触发指定日期的每日复盘计算，生成 Markdown 报告。

**curl 命令**

```bash
curl -X POST "http://localhost:8000/api/v1/market-insight/daily-report?trade_date=2023-01-01"
```

**入参**

*   `trade_date` (date, query, required): 交易日期。

### GET /market-insight/sentiment-metrics

**功能描述**

获取指定交易日的市场情绪分析，包括连板梯队、赚钱效应、炸板率。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/market-insight/sentiment-metrics?trade_date=2023-01-01"
```

**入参**

*   `trade_date` (date, query, required): 交易日期。

### GET /market-insight/capital-flow

**功能描述**

获取指定交易日的资金流向分析，包括龙虎榜汇总和板块资金流向。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/market-insight/capital-flow?trade_date=2023-01-01&sector_type=概念资金流"
```

**入参**

*   `trade_date` (date, query, required): 交易日期。
*   `sector_type` (string, query, optional): 板块类型（如'概念资金流'）。

---

## Knowledge Center

### POST /knowledge-graph/concept-relations

**功能描述**

手动创建概念间关系，状态默认为 CONFIRMED。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations -H "Content-Type: application/json" -d '{
  "source_concept_code": "C001",
  "target_concept_code": "C002",
  "relation_type": "UPSTREAM",
  "reason": "...",
  "note": "..."
}'
```

**入参** (Request Body)

*   `source_concept_code` (string, required): 源概念代码。
*   `target_concept_code` (string, required): 目标概念代码。
*   `relation_type` (string, required): 关系类型。
*   `note` (string, optional): 备注。
*   `reason` (string, optional): 原因。

### GET /knowledge-graph/concept-relations

**功能描述**

支持多条件筛选的概念关系列表查询。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/concept-relations?source_concept_code=C001&limit=50"
```

**入参**

*   `source_concept_code` (string, query, optional)
*   `target_concept_code` (string, query, optional)
*   `relation_type` (string, query, optional)
*   `source_type` (string, query, optional)
*   `status` (string, query, optional)
*   `limit` (integer, query, optional, default: 100)
*   `offset` (integer, query, optional, default: 0)

### GET /knowledge-graph/concept-relations/{relation_id}

**功能描述**

根据 ID 查询单条概念关系记录。

**curl 命令**

```bash
curl -X GET http://localhost:8000/api/v1/knowledge-graph/concept-relations/123
```

**入参**

*   `relation_id` (integer, path, required): 关系ID。

### PUT /knowledge-graph/concept-relations/{relation_id}

**功能描述**

更新概念关系（主要用于确认或拒绝 LLM 推荐）。

**curl 命令**

```bash
curl -X PUT http://localhost:8000/api/v1/knowledge-graph/concept-relations/123 -H "Content-Type: application/json" -d '{"status": "CONFIRMED"}'
```

**入参**

*   `relation_id` (integer, path, required): 关系ID。
*   `status` (string, body, optional): 新的状态。

### DELETE /knowledge-graph/concept-relations/{relation_id}

**功能描述**

删除指定 ID 的概念关系记录。

**curl 命令**

```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge-graph/concept-relations/123
```

**入参**

*   `relation_id` (integer, path, required): 关系ID。

### POST /knowledge-graph/concept-relations/llm-suggest

**功能描述**

基于 LLM 分析推荐概念间关系，结果写入数据库待人工确认。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations/llm-suggest -H "Content-Type: application/json" -d '{
  "concept_codes_with_names": {"C001": "Concept A", "C002": "Concept B"},
  "min_confidence": 0.7
}'
```

**入参** (Request Body)

*   `concept_codes_with_names` (object, required): 包含概念代码和名称的字典。
*   `min_confidence` (float, optional, default: 0.7): 最低置信度。

### POST /knowledge-graph/concept-relations/sync

**功能描述**

将数据库中已确认的概念关系同步到 Neo4j 图谱。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations/sync -H "Content-Type: application/json" -d '{"mode": "full", "batch_size": 100}'
```

**入参** (Request Body)

*   `mode` (string, required): 同步模式 ("full" 或 "incremental")。
*   `batch_size` (integer, optional, default: 100): 每批处理数量。

### GET /knowledge-graph/concepts/{code}/relations

**功能描述**

查询指定概念的直接关系（上下游、竞争等）。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/concepts/C001/relations?direction=both"
```

**入参**

*   `code` (string, path, required): 概念代码。
*   `direction` (string, query, optional, default: 'both'): 查询方向 ('outgoing', 'incoming', 'both')。
*   `relation_types` (array, query, optional): 关系类型列表。

### GET /knowledge-graph/concepts/{code}/chain

**功能描述**

查询指定概念的产业链路径。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/concepts/C001/chain?max_depth=3"
```

**入参**

*   `code` (string, path, required): 概念代码。
*   `direction` (string, query, optional, default: 'outgoing'): 遍历方向。
*   `max_depth` (integer, query, optional, default: 3): 最大遍历深度。
*   `relation_types` (array, query, optional): 关系类型列表。

---

## Coordinator

### POST /research

**功能描述**

根据指定标的与专家列表，并行执行研究分析并汇总结果。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/research -H "Content-Type: application/json" -d '{
  "symbol": "AAPL",
  "experts": ["technical_analyst", "financial_auditor"],
  "options": {},
  "skip_debate": false
}'
```

**入参** (Request Body)

*   `symbol` (string, required): 股票代码。
*   `experts` (array, required): 专家类型列表。
*   `options` (object, optional): 各专家可选参数。
*   `skip_debate` (boolean, optional, default: false): 是否跳过辩论阶段。

### POST /research/{session_id}/retry

**功能描述**

对已有会话中失败的专家发起重试。

**curl 命令**

```bash
curl -X POST http://localhost:8000/api/v1/research/your-session-uuid/retry -H "Content-Type: application/json" -d '{"skip_debate": false}'
```

**入参**

*   `session_id` (UUID, path, required): 研究会话ID。
*   `skip_debate` (boolean, body, optional, default: false): 是否跳过辩论阶段。

### GET /research/sessions

**功能描述**

分页查询研究会话列表，支持按股票代码和时间范围筛选。

**curl 命令**

```bash
curl -X GET "http://localhost:8000/api/v1/research/sessions?symbol=AAPL&limit=10"
```

**入参**

*   `symbol` (string, query, optional): 股票代码。
*   `created_after` (datetime, query, optional): 创建时间起始。
*   `created_before` (datetime, query, optional): 创建时间截止。
*   `skip` (integer, query, optional, default: 0): 跳过条数。
*   `limit` (integer, query, optional, default: 20): 每页条数。

### GET /research/sessions/{session_id}

**功能描述**

查询单次研究会话详情及全部节点执行记录。

**curl 命令**

```bash
curl -X GET http://localhost:8000/api/v1/research/sessions/your-session-uuid
```

**入参**

*   `session_id` (UUID, path, required): 会话ID。

### GET /research/sessions/{session_id}/llm-calls

**功能描述**

返回该会话下所有 LLM 调用的审计日志。

**curl 命令**

```bash
curl -X GET http://localhost:8000/api/v1/research/sessions/your-session-uuid/llm-calls
```

**入参**

*   `session_id` (UUID, path, required): 会话ID。

### GET /research/sessions/{session_id}/api-calls

**功能描述**

返回该会话下所有外部 API 调用的审计日志。

**curl 命令**

```bash
curl -X GET http://localhost:8000/api/v1/research/sessions/your-session-uuid/api-calls
```

**入参**

*   `session_id` (UUID, path, required): 会话ID。
