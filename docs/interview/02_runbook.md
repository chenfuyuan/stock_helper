# Runbook - 如何本地运行/测试/构建/配置

## A) 项目构建系统判断

**构建系统**: **pip + requirements.txt** (传统 Python 项目管理)

**判断依据**：
- 存在 `requirements.txt` 文件（非 `pyproject.toml` 管理依赖）
- `pyproject.toml` 仅用于工具配置（Black/Mypy/Pytest），非依赖管理
- `Makefile` 中使用 `pip install -r requirements.txt`
- 无 `poetry.lock` 或 `Pipfile.lock`

**环境管理建议**: 使用 `venv` 或 `conda`（项目包含 `environment.yml`）

---

## B) 常用命令清单

### 环境准备

```bash
# 1. 创建虚拟环境 (任选其一)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 或使用 conda
conda env create -f environment.yml
conda activate stock_helper

# 2. 安装依赖
pip install -r requirements.txt
```

### 运行应用

```bash
# 方式一：使用 Makefile
make run

# 方式二：直接运行 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 方式三：Docker Compose（推荐，包含完整依赖服务）
docker compose up -d --build
docker compose logs -f app
```

### 测试

```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=src --cov-report=term-missing

# 运行特定测试文件
pytest tests/unit/test_some_module.py

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/e2e/
```

### 代码质量检查

```bash
# 完整 CI 检查（lint + test）
make ci-check

# 仅 lint
make lint

# 仅 format
make format

# 自动修复代码质量
make fix-quality
```

### 数据库迁移

```bash
# 升级到最新版本
alembic upgrade head

# 降级一个版本
alembic downgrade -1

# 查看当前版本
alembic current

# 创建新迁移
alembic revision --autogenerate -m "描述"

# 查看待应用的迁移
alembic history
```

### Docker 相关

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看应用日志
docker compose logs -f app

# 查看数据库日志
docker compose logs -f db

# 停止所有服务
docker compose down

# 删除数据卷（重置数据库）
docker compose down -v

# 重启单个服务
docker compose restart app
```

---

## C) 关键配置来源

### 配置文件清单

| 文件 | 用途 | 环境 |
|------|------|------|
| `.env` | 主配置文件（数据库/LLM/Tushare） | 所有环境 |
| `.env.example` | 配置模板 | - |
| `src/shared/config.py` | 配置类定义（Settings） | 代码层 |
| `docker-compose.yml` | Docker 环境变量注入 | Docker |
| `alembic.ini` | 数据库迁移配置 | Alembic |

### 环境变量（.env）

```bash
# 项目基础配置
PROJECT_NAME="Stock Helper"
ENVIRONMENT=local  # local/dev/prod

# 数据库配置
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=stock_helper
POSTGRES_PORT=5432

# Tushare 数据源
TUSHARE_TOKEN=<your_token>

# LLM 配置 (Bocha AI)
BOCHA_API_KEY=<your_api_key>
BOCHA_BASE_URL=https://api.bochaai.com

# Neo4j 图数据库
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 配置加载顺序

1. **环境变量** > `.env` 文件 > 默认值
2. Pydantic Settings 自动加载（`src/shared/config.py:60-64`）
3. `.env` 中多余字段被 `extra = "ignore"` 忽略（允许模块专属配置）

### 模块专属配置来源

| 模块 | 配置前缀 | 读取位置 |
|------|----------|----------|
| Data Engineering | `TUSHARE_*`, `AKSHARE_*` | 各自 service/config |
| LLM Platform | `BOCHA_*`, `LLM_*` | `modules/llm_platform/` |
| Knowledge Center | `NEO4J_*` | `modules/knowledge_center/` |
| Scheduler | `SYNC_*` | `modules/foundation/` |

---

## D) 配置项表格

| 配置项 | 用途 | 默认值 | 读取位置 | 生产注入方式 |
|--------|------|--------|----------|--------------|
| `PROJECT_NAME` | 项目名称 | "Stock Helper" | `config.py:13` | 环境变量 |
| `API_V1_STR` | API 前缀 | "/api/v1" | `config.py:14` | 代码常量 |
| `ENVIRONMENT` | 运行环境 | "local" | `config.py:17` | 环境变量 |
| `BACKEND_CORS_ORIGINS` | CORS 域名 | [] | `config.py:20-32` | 环境变量（逗号分隔） |
| `POSTGRES_SERVER` | DB 主机 | "localhost" | `config.py:35` | 环境变量/.env |
| `POSTGRES_USER` | DB 用户 | "postgres" | `config.py:36` | 环境变量/.env |
| `POSTGRES_PASSWORD` | DB 密码 | "password" | `config.py:37` | 环境变量/.env/Secrets |
| `POSTGRES_DB` | DB 名称 | "stock_helper" | `config.py:38` | 环境变量/.env |
| `SQLALCHEMY_DATABASE_URI` | 完整 DB URI | 自动构建 | `config.py:40-58` | 直接设置或自动构建 |
| `TUSHARE_TOKEN` | Tushare API Token | - | 模块读取 | 环境变量/Secrets |
| `BOCHA_API_KEY` | Bocha LLM API Key | - | `modules/llm_platform/` | 环境变量/Secrets |
| `BOCHA_BASE_URL` | Bocha LLM Base URL | https://api.bochaai.com | `modules/llm_platform/` | 环境变量 |
| `NEO4J_URI` | Neo4j 连接 | bolt://neo4j:7687 | `modules/knowledge_center/` | 环境变量 |
| `NEO4J_USER` | Neo4j 用户 | neo4j | `modules/knowledge_center/` | 环境变量 |
| `NEO4J_PASSWORD` | Neo4j 密码 | password | `modules/knowledge_center/` | 环境变量/Secrets |

### 生产环境 Secrets 管理建议

1. **Kubernetes**: 使用 `Secret` 资源注入敏感配置
2. **Docker Swarm**: 使用 `docker secret`
3. **云服务器**: 使用云厂商 Secrets Manager（AWS Secrets Manager/阿里云 ACM）
4. **最简单**: CI/CD 流水线中设置环境变量

---

## E) 常见启动失败排查

### 1. 端口占用

**症状**: `Address already in use` 或 `OSError: [Errno 48]`

```bash
# 检查 8000 端口占用
lsof -i :8000

# 杀死占用进程
kill -9 <PID>

# 或修改端口
uvicorn src.main:app --port 8001
```

### 2. 数据库连接失败

**症状**: `sqlalchemy.exc.OperationalError: could not connect to server`

**排查步骤**:

```bash
# 1. 检查 PostgreSQL 是否运行
docker compose ps db

# 2. 测试数据库连接
docker compose exec db pg_isready -U postgres

# 3. 查看数据库日志
docker compose logs db

# 4. 本地直连测试（Docker 外）
psql -h localhost -U postgres -d stock_helper
```

**常见原因**:
- `POSTGRES_SERVER` 配置错误（Docker 内用 `db`，本地用 `localhost`）
- 数据库未启动完成就启动应用
- 防火墙/网络问题

### 3. 缺少配置

**症状**: `ValidationError` 或 `KeyError`

```bash
# 检查环境变量
env | grep -E "(POSTGRES|TUSHARE|BOCHA|NEO4J)"

# 对比 .env.example
diff .env .env.example
```

**解决**: 复制模板并填充必要值

```bash
cp .env.example .env
# 编辑 .env，至少填写 TUSHARE_TOKEN 和 BOCHA_API_KEY
```

### 4. 依赖服务缺失（Neo4j）

**症状**: Neo4j 相关初始化失败，日志包含 `connection refused`

**排查**:

```bash
# 检查 Neo4j 容器状态
docker compose ps neo4j

# 查看 Neo4j 日志
docker compose logs neo4j

# 测试 Bolt 连接
docker compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1;"
```

### 5. Alembic 迁移失败

**症状**: `alembic.util.exc.CommandError` 或 `sqlalchemy.exc.ProgrammingError`

```bash
# 检查当前迁移版本
alembic current

# 查看迁移历史
alembic history

# 清理并重新开始（仅开发环境！）
docker compose down -v
docker compose up -d db
alembic upgrade head
```

### 6. Tushare Token 无效

**症状**: API 返回 401/403 或数据为空

**解决**:
1. 访问 https://tushare.pro/register 注册
2. 获取个人 Token
3. 更新 `.env` 中的 `TUSHARE_TOKEN`

### 7. LLM API 调用失败

**症状**: `openai.APIError` 或 `401 Unauthorized`

**排查**:

```bash
# 检查配置
grep BOCHA .env

# 测试 API
curl -H "Authorization: Bearer $BOCHA_API_KEY" $BOCHA_BASE_URL/v1/models
```

---

## 快速启动检查清单

```bash
# 1. 环境变量准备
[ -f .env ] || cp .env.example .env
# 编辑 .env，填写 TUSHARE_TOKEN 和 BOCHA_API_KEY

# 2. Docker 服务启动
docker compose up -d --build

# 3. 等待服务健康
docker compose ps  # 所有服务应为 healthy

# 4. 测试健康检查
curl http://localhost:8000/api/v1/health

# 5. 访问 API 文档
open http://localhost:8000/api/v1/docs
```

---

## 开发环境 vs 生产环境差异

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| `ENVIRONMENT` | local/dev | prod |
| `POSTGRES_SERVER` | db / localhost | 云数据库地址 |
| `DEBUG` | true | false |
| 日志级别 | DEBUG | INFO/WARNING |
| CORS | 允许 localhost | 仅允许生产域名 |
| 并发 worker | 1 | 多 worker（gunicorn） |
