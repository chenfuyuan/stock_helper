# API 参考手册

本文档提供了 Stock Helper 系统中可用 REST API 接口的概览。

**基础 URL**: `/api/v1`

## 身份验证
目前 API 尚未强制执行全局身份验证，但特定操作可能需要根据配置提供令牌或 API 密钥（例如：Tushare Token）。

## 股票数据 (`/stocks`)

管理股票市场数据。

- **GET** `/stocks/sync/list`: 触发股票基础列表同步。
- **GET** `/stocks/sync/daily`: 触发日线行情数据同步。
- **GET** `/stocks/sync/finance`: 触发财务报表同步。
- **GET** `/stocks/basic/{symbol}`: 获取特定股票的基础信息。

## 调度器 (`/scheduler`)

管理后台作业和任务。

- **GET** `/scheduler/status`: 获取调度器的整体状态。
- **GET** `/scheduler/jobs`: 列出所有已注册的作业。
- **POST** `/scheduler/jobs/{job_id}/trigger`: 立即触发一个作业。
- **POST** `/scheduler/jobs/{job_id}/start`: 启动一个已暂停的作业。
- **POST** `/scheduler/jobs/{job_id}/stop`: 暂停/停止一个作业。

## LLM 平台 (`/llm-platform`)

管理 LLM 配置并提供聊天接口。

### 配置管理 (`/llm-platform/configs`)
- **GET** `/`: 列出所有 LLM 配置。
- **POST** `/`: 创建新的 LLM 配置。
- **GET** `/{alias}`: 获取特定配置详情。
- **PUT** `/{alias}`: 更新配置。
- **DELETE** `/{alias}`: 删除配置。
- **POST** `/refresh`: 强制系统从数据库重新加载配置。

### 聊天接口 (`/llm-platform/chat`)
- **POST** `/completions`: 使用指定 LLM 或根据标签自动选择模型生成文本。
  - **请求体**: `{ "prompt": "...", "alias": "deepseek-v3" }`

## 健康检查 (`/health`)

- **GET** `/health`: 如果服务运行正常，返回 200 OK。
