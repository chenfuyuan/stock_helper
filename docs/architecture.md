# 架构概览

本项目采用 **领域驱动设计 (DDD)** 原则构建，以确保业务逻辑与基础设施细节之间的可维护性、可扩展性和松耦合。

## 核心分层

应用遵循整洁架构 (Clean Architecture) 范式，分为四个截然不同的层：

### 1. 展示层 (`presentation`)
- **职责**: 处理外部交互（HTTP 请求、CLI 命令、定时任务）。
- **组件**:
  - `rest/`: FastAPI 路由和控制器。
  - `jobs/`: 定时任务 (APScheduler)。
- **规则**: 此层**不应**包含业务规则。它仅负责解析输入、调用应用层并格式化输出。

### 2. 应用层 (`application`)
- **职责**: 编排领域逻辑和基础设施以实现用例。
- **组件**:
  - `services/`: 协调领域实体和存储库的应用服务。
  - `commands/`: CQRS 命令处理器（例如：`sync_stock_list_cmd.py`）。
  - `dtos.py`: 数据传输对象。
- **规则**: 不包含业务逻辑状态，但负责指导数据流向。

### 3. 领域层 (`domain`)
- **职责**: 代表业务概念、规则和逻辑。这是软件的核心。
- **组件**:
  - `model/` 或 `entities/`: 代表业务实体的纯 Python 对象（例如：`Stock`、`LLMConfig`）。
  - `ports/`: 定义存储库和外部服务合约的接口（抽象基类）。
- **规则**: **对外部层（数据库、Web 等）零依赖**。纯 Python 代码。

### 4. 基础设施层 (`infrastructure`)
- **职责**: 为领域层中定义的接口提供具体实现。
- **组件**:
  - `persistence/`: 数据库模型 (SQLAlchemy)、存储库实现。
  - `external_apis/`: 第三方 API 客户端（例如：Tushare、OpenAI）。
  - `adapters/`: 特定技术的适配器。
- **规则**: 依赖于领域层和应用层。

## 模块结构

项目被划分为垂直模块（限界上下文）：

- **`data_engineering`**: 处理股票市场数据的获取、处理和存储。
- **`llm_platform`**: 管理大语言模型配置和使用。
- **`shared`**: 跨模块使用的通用工具、基类和配置。

## 关键模式

### 存储库模式 (Repository Pattern)
我们使用存储库模式将领域模型与数据存储解耦。
- **接口**: 定义在 `domain/ports/repositories`。
- **实现**: 定义在 `infrastructure/persistence/repositories`。

### 依赖注入 (Dependency Injection)
依赖项（如存储库和服务）被注入，通常使用 FastAPI 的 `Depends` 机制，或者在组合根（主入口点或服务工厂）中手动构建。

### CQRS (命令查询职责分离)
对于复杂操作，特别是数据同步，我们将读写操作分离为命令和查询（在本项目中简化为 Command 类）。
