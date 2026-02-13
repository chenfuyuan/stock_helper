-- =============================================================================
-- 通过 SQL 查询辅助排查研究流水线 / LLM / 外部 API 调用问题
-- 表：research_sessions, node_executions, llm_call_logs, external_api_call_logs
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. 按会话看整体结果：最近 N 次研究会话（状态、耗时、是否完成）
-- -----------------------------------------------------------------------------
SELECT id, symbol, status, trigger_source,
       created_at, completed_at, duration_ms
FROM research_sessions
ORDER BY created_at DESC
LIMIT 20;


-- -----------------------------------------------------------------------------
-- 2. 看某次会话里哪个节点出错（替换 <session_id> 为 research_sessions.id）
-- -----------------------------------------------------------------------------
SELECT node_type, status, error_type, error_message,
        started_at, completed_at, duration_ms
FROM node_executions
WHERE session_id = '<session_id>'
ORDER BY started_at;


-- -----------------------------------------------------------------------------
-- 3. 看该会话的 LLM 调用（成功/失败、耗时、错误信息）
-- -----------------------------------------------------------------------------
SELECT caller_module, caller_agent, model_name, status,
    latency_ms, error_message, created_at
FROM llm_call_logs
WHERE session_id = '<session_id>'
ORDER BY created_at;

-- 需要看具体 prompt/回复时（数据量大，慎用）：
SELECT caller_agent, status,
       LEFT(prompt_text, 500) AS prompt_preview,
       LEFT(completion_text, 500) AS completion_preview,
       error_message
FROM llm_call_logs
WHERE session_id = '<session_id>';


-- -----------------------------------------------------------------------------
-- 4. 看该会话的外部 API 调用（如博查搜索）
-- -----------------------------------------------------------------------------
SELECT service_name, operation, status_code, status, latency_ms,
       error_message, created_at
FROM external_api_call_logs
WHERE session_id = '<session_id>'
ORDER BY created_at;


-- -----------------------------------------------------------------------------
-- 5. 一条链式排查：最近一次失败/部分完成的会话 + 其节点与 LLM 调用
-- -----------------------------------------------------------------------------
WITH last_bad AS (
  SELECT id, symbol, status, created_at
  FROM research_sessions
  WHERE status IN ('failed', 'partial')
  ORDER BY created_at DESC
  LIMIT 1
)
SELECT 'session' AS layer, id::text AS id_or_type, status, NULL::text AS detail
FROM last_bad
UNION ALL
SELECT 'node', n.node_type, n.status, n.error_message
FROM node_executions n, last_bad l
WHERE n.session_id = l.id
UNION ALL
SELECT 'llm', COALESCE(c.caller_agent, c.caller_module), c.status, c.error_message
FROM llm_call_logs c, last_bad l
WHERE c.session_id = l.id
ORDER BY layer, id_or_type;


-- -----------------------------------------------------------------------------
-- 6. 按 symbol 查某标的最近会话（列表/分页）
-- -----------------------------------------------------------------------------
SELECT id, symbol, status, created_at, completed_at, duration_ms
FROM research_sessions
WHERE symbol = 'AAPL'   -- 或 000001.SZ 等
ORDER BY created_at DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- 排查顺序建议
-- -----------------------------------------------------------------------------
-- 1. research_sessions 找到异常会话的 id、status
-- 2. node_executions 找到 status = 'failed' 的 node_type、error_message
-- 3. 同一 session_id 下查 llm_call_logs / external_api_call_logs 判断是 LLM 还是外部 API 失败
