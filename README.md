# Stock Helper

## Docker 运行

```bash
# 复制环境变量并填写必要配置（如 TUSHARE_TOKEN、数据库等）
cp .env.example .env

# 启动应用与数据库
docker compose up -d

# 查看日志
docker compose logs -f app
```

应用默认端口 **8000**，健康检查：`GET http://localhost:8000/api/v1/health`。

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
