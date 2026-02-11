# Stock Helper

## Docker 运行

**前置**：需已安装 [Docker](https://docs.docker.com/get-docker/) 与 [Docker Compose](https://docs.docker.com/compose/install/)。

```bash
# 1. 复制环境变量（首次或需要改配置时）
cp .env.example .env
# 编辑 .env，至少可先保留默认；TUSHARE_TOKEN、LLM 等按需填写

# 2. 构建并启动（数据库 + 应用，自动执行 alembic 迁移）
docker compose up -d --build

# 3. 查看应用日志
docker compose logs -f app
```

- 应用端口：**8000**  
- 健康检查：`GET http://localhost:8000/api/v1/health`  
- API 文档：`http://localhost:8000/api/v1/docs`  

仅停止：`docker compose down`。连数据卷一起删：`docker compose down -v`。

## 技术分析接口（按股票测试）

对指定股票运行技术分析（依赖已同步的日线数据与 LLM 配置）：

```bash
# 指定股票代码，分析基准日可选（默认当天）
curl -s "http://localhost:8000/api/v1/research/technical-analysis?ticker=000001.SZ&analysis_date=2024-01-15"
```

- **ticker**（必填）：股票代码，如 `000001.SZ`
- **analysis_date**（可选）：分析基准日 `YYYY-MM-DD`，不传则使用当前日期

返回为 JSON：`signal`（BULLISH/BEARISH/NEUTRAL）、`confidence`、`summary_reasoning`、`key_technical_levels`、`risk_warning`。

**注意**：需先同步该标的日线（如通过 `/api/v1/stocks/sync/daily` 等），并已在 LLM 平台配置可用模型，否则接口可能返回 422/500。

API 文档：`http://localhost:8000/api/v1/docs`。
