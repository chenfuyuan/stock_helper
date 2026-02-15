## ADDED Requirements

### Requirement: 僵死任务超时检测与自动恢复

系统 SHALL 在 `SyncEngine.run_history_sync` 的互斥检查逻辑中增加基于 `updated_at` 的超时判断。当发现 RUNNING 状态的同类型 `SyncTask` 时，系统 SHALL 计算 `now - updated_at` 的时间差。若超过可配置的超时阈值（`SYNC_TASK_STALE_TIMEOUT_MINUTES`，默认 10 分钟），系统 SHALL 将该任务标记为 FAILED（失败原因记录为"超时自动标记：updated_at 超过阈值"），并允许启动新任务。若未超时，系统 SHALL 保持现有行为——拒绝启动新任务。

#### Scenario: RUNNING 任务超时自动标记为 FAILED

- **WHEN** 调用 `SyncEngine.run_history_sync`，已存在同类型 RUNNING 状态的 `SyncTask`，且其 `updated_at` 距今超过 10 分钟（默认阈值）
- **THEN** 系统 SHALL 将该 RUNNING 任务标记为 FAILED，记录超时原因，然后创建新的 `SyncTask` 并正常执行同步

#### Scenario: RUNNING 任务未超时仍拒绝新任务

- **WHEN** 调用 `SyncEngine.run_history_sync`，已存在同类型 RUNNING 状态的 `SyncTask`，且其 `updated_at` 距今在 10 分钟以内
- **THEN** 系统 SHALL 拒绝启动新任务，返回已存在的 RUNNING 任务信息（与现有行为一致）

#### Scenario: 超时阈值可配置

- **WHEN** 设置环境变量 `SYNC_TASK_STALE_TIMEOUT_MINUTES=5`
- **THEN** 系统 SHALL 使用 5 分钟作为超时阈值判断僵死任务

---

### Requirement: TuShare 频率超限异常退避重试

`TushareClient._rate_limited_call()` SHALL 在检测到 TuShare 返回频率超限异常时，自动执行指数退避重试。频率超限异常的判断 SHALL 基于异常消息中包含"频率"、"每分钟"等关键词。重试策略：第 1 次等待 3 秒，第 2 次 6 秒，第 3 次 12 秒（base=3s，factor=2）。超过 3 次重试后 SHALL 抛出原始异常由上层处理。每次重试 SHALL 记录 WARNING 级别日志，包含已重试次数和等待时间。

#### Scenario: 首次频率超限自动重试成功

- **WHEN** TuShare API 调用返回频率超限异常，第 1 次重试成功
- **THEN** 系统 SHALL 等待 3 秒后重试，重试成功后正常返回结果，上层调用方无感知

#### Scenario: 多次重试后成功

- **WHEN** TuShare API 连续 2 次返回频率超限异常，第 3 次成功
- **THEN** 系统 SHALL 依次等待 3 秒、6 秒后重试，第 3 次成功后正常返回结果

#### Scenario: 超过最大重试次数后抛出异常

- **WHEN** TuShare API 连续 4 次返回频率超限异常（首次 + 3 次重试均失败）
- **THEN** 系统 SHALL 抛出原始异常，由上层调用方处理

#### Scenario: 非频率超限异常不触发重试

- **WHEN** TuShare API 调用抛出网络超时或其他非频率相关异常
- **THEN** 系统 SHALL 直接抛出异常，不执行退避重试

---

## MODIFIED Requirements

### Requirement: 限速策略收敛到 Infrastructure 层

所有 Tushare API 调用 SHALL 且仅 SHALL 通过 `TushareClient._rate_limited_call()` 进行限速。Application 层的同步 Use Case SHALL NOT 包含任何限速逻辑（如 `Semaphore`、`asyncio.sleep` 用于限速目的）。限速 SHALL 采用**滑动窗口算法**（Sliding Window Log）：在 `TUSHARE_RATE_LIMIT_WINDOW_SECONDS`（默认 60 秒）的时间窗口内，允许最多 `TUSHARE_RATE_LIMIT_MAX_CALLS`（默认 195 次，预留安全余量）调用。当窗口内已达上限时，系统 SHALL 等待最早的时间戳滑出窗口后再执行调用。限速参数 SHALL 从配置中读取，而非硬编码。

#### Scenario: Use Case 无限速代码

- **WHEN** 审查 Application 层的所有同步 Use Case 代码
- **THEN** SHALL NOT 存在 `asyncio.Semaphore`、`asyncio.sleep`（用于限速目的）或其他限速控制逻辑

#### Scenario: 滑动窗口限速参数可配置

- **WHEN** 通过环境变量设置 `TUSHARE_RATE_LIMIT_MAX_CALLS=180` 和 `TUSHARE_RATE_LIMIT_WINDOW_SECONDS=60`
- **THEN** `TushareClient._rate_limited_call()` 在 60 秒窗口内最多允许 180 次调用

#### Scenario: 批量调用场景下吞吐量提升

- **WHEN** 系统在短时间内连续发起 100 次 TuShare API 调用，且当前窗口内已有 0 次记录
- **THEN** 前 100 次调用 SHALL 几乎无等待地连续执行（突发友好），总耗时远小于 100 × 0.35s = 35s

#### Scenario: 窗口内达到上限时等待

- **WHEN** 60 秒窗口内已完成 195 次调用，系统发起第 196 次调用
- **THEN** 系统 SHALL 等待最早的调用时间戳滑出 60 秒窗口后再执行第 196 次调用

---

### Requirement: 配置外部化

系统 SHALL 将以下硬编码值提取为可配置项（通过 `DataEngineeringConfig`，支持环境变量覆盖）：日线历史同步批大小（默认 50）、财务历史同步批大小（默认 100）、财务历史同步起始日期（默认 `20200101`）、增量同步缺数补齐上限（默认 300）、失败最大重试次数（默认 3）、**TuShare 滑动窗口最大调用次数**（默认 195）、**TuShare 滑动窗口时间秒数**（默认 60）、**同步任务僵死超时分钟数**（默认 10）。Use Case 和 SyncEngine SHALL 从配置中读取这些值，而非硬编码。

#### Scenario: 通过环境变量覆盖批大小

- **WHEN** 设置环境变量 `SYNC_DAILY_HISTORY_BATCH_SIZE=100`
- **THEN** 历史日线同步使用 100 作为每批处理量，而非默认的 50

#### Scenario: 通过环境变量覆盖滑动窗口参数

- **WHEN** 设置环境变量 `TUSHARE_RATE_LIMIT_MAX_CALLS=180`
- **THEN** TuShare 滑动窗口限速器使用 180 作为窗口内最大调用次数

#### Scenario: 通过环境变量覆盖僵死超时

- **WHEN** 设置环境变量 `SYNC_TASK_STALE_TIMEOUT_MINUTES=5`
- **THEN** 同步引擎使用 5 分钟作为僵死任务超时判断阈值

#### Scenario: 使用默认配置

- **WHEN** 未设置任何同步相关环境变量
- **THEN** 系统 SHALL 使用默认值运行（批大小 50/100、起始日期 20200101、滑动窗口 195次/60s、僵死超时 10 分钟等）
