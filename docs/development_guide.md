# 开发指南

本指南涵盖了 Stock Helper 项目的环境搭建、开发流程和编码标准。

## 环境搭建

### 前提条件
- **Python 3.10+**
- **Docker & Docker Compose** (用于数据库)
- **Conda** (推荐用于 Python 环境管理)

### 1. 克隆与依赖安装

```bash
# 克隆仓库
git clone <repository-url>
cd stock_helper

# 创建 Conda 环境
conda create -n stock_helper python=3.10
conda activate stock_helper

# 安装依赖
make install
# 或者手动安装：
pip install -r requirements.txt
```

### 2. 配置

复制示例环境文件并进行配置：

```bash
cp .env.example .env
```

**必填变量：**
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: 数据库凭据。
- `TUSHARE_TOKEN`: 您的 Tushare API 令牌（数据同步必需）。

### 3. 数据库设置

使用 Docker 启动 PostgreSQL 数据库：

```bash
docker-compose up -d db
```

运行 Alembic 迁移以创建数据表：

```bash
alembic upgrade head
```

## 运行应用

### 本地开发

启动开启热重载的 FastAPI 服务器：

```bash
make run
# 或者
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 运行

在容器中运行整个技术栈（应用 + 数据库）：

```bash
docker-compose up --build
```

## 数据库迁移

我们使用 **Alembic** 处理数据库架构变更。

### 创建新迁移

修改 `src/modules/*/infrastructure/persistence/models/` 中的 SQLAlchemy 模型后，生成迁移脚本：

```bash
alembic revision --autogenerate -m "变更描述"
```

**在应用之前，请检查 `alembic/versions/` 中生成的迁移文件**以确保其正确性。

### 应用迁移

```bash
alembic upgrade head
```

## 测试

我们使用 **pytest** 进行测试。

### 运行测试

```bash
make test
# 或者
pytest
```

### 编写测试
- **单元测试**: 放置在 `tests/domain` 或 `tests/application`。需 Mock 外部依赖。
- **集成测试**: 放置在 `tests/integration`。可能需要真实的数据库或 Mock 的 API 响应。

## 代码风格与标准

### Python
- **类型提示 (Type Hints)**: **强制要求**。使用 `typing` 模块或 Python 3.10+ 语法（如 `str | int`）。
- **文档字符串 (Docstrings)**: 所有公开模块、类和函数均需提供。
- **格式化**: 遵循 PEP 8。
- **日志**: 使用 `loguru` (`from loguru import logger`)。

### 架构规则
- **依赖规则**: 领域层不得依赖外部层。
- **注入**: 通过 `__init__` 或 FastAPI `Depends` 注入依赖。避免使用全局状态。
- **禁止魔术字符串**: 使用枚举 (Enums) 或常量。

## 调度器 (Scheduler)

项目使用 `APScheduler` 处理后台任务。
- **任务 (Jobs)**: 定义在 `src/modules/*/presentation/jobs/`。
- **管理**: 使用 Scheduler API 启动/停止/触发任务。
