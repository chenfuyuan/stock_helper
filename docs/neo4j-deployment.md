# Neo4j 部署与运维指南

> 本文档面向开发者，说明如何在本地开发环境中搭建和管理 Neo4j 图数据库。

---

## 1. 概述

Stock Helper 使用 **Neo4j 5 Community Edition** 作为知识图谱的存储引擎，通过 Docker Compose 统一管理。Neo4j 运行在与 PostgreSQL 相同的 Docker 网络（`stock_helper_net`）中，应用容器通过 Bolt 协议（`bolt://neo4j:7687`）连接。

---

## 2. 环境变量配置

在 `.env` 文件中新增以下配置项（参考 `.env.example`）：

```env
# Neo4j 配置
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
```

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `NEO4J_URI` | Bolt 协议连接地址。容器间通信使用服务名 `neo4j` | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j 用户名 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密码（**必须修改默认值**，至少 8 个字符） | — |

> **安全提示**：切勿将真实密码提交到版本控制。`.env` 已在 `.gitignore` 中。

---

## 3. Docker Compose 服务定义

`docker-compose.yml` 中新增的 `neo4j` 服务配置如下：

```yaml
neo4j:
  image: public.ecr.aws/docker/library/neo4j:5-community
  container_name: stock_helper_neo4j
  ports:
    - "7474:7474"   # Neo4j Browser (HTTP)
    - "7687:7687"   # Bolt 协议
  environment:
    - NEO4J_AUTH=${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD}
    - NEO4J_PLUGINS=["apoc"]
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
  networks:
    - stock_helper_net
  healthcheck:
    test: ["CMD-SHELL", "cypher-shell -u ${NEO4J_USER:-neo4j} -p ${NEO4J_PASSWORD} 'RETURN 1'"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
```

同时在 `volumes` 部分新增：

```yaml
volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
```

`app` 服务新增依赖：

```yaml
app:
  depends_on:
    db:
      condition: service_healthy
    neo4j:
      condition: service_healthy
```

---

## 4. 启动与验证

### 4.1 首次启动

```bash
# 启动所有服务（包含 Neo4j）
docker compose up -d

# 查看 Neo4j 容器日志，确认启动成功
docker compose logs -f neo4j
```

等待看到 `Started.` 日志即表示 Neo4j 就绪。

### 4.2 验证连接

**方式一：Neo4j Browser**

打开浏览器访问 [http://localhost:7474](http://localhost:7474)，使用配置的用户名和密码登录。

**方式二：命令行验证**

```bash
# 在 neo4j 容器内执行 Cypher 查询
docker compose exec neo4j cypher-shell -u neo4j -p <your_password> "RETURN 'Neo4j is running' AS status"
```

**方式三：从 app 容器内验证**

```bash
docker compose exec app python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', '<your_password>'))
with driver.session() as session:
    result = session.run('RETURN 1 AS num')
    print(f'连接成功: {result.single()[\"num\"]}')
driver.close()
"
```

---

## 5. 端口说明

| 端口 | 协议 | 用途 |
| --- | --- | --- |
| `7474` | HTTP | Neo4j Browser Web 管理界面 |
| `7687` | Bolt | 应用程序连接端口（Python 驱动使用此端口） |

> 如果本地端口冲突，可在 `docker-compose.yml` 中调整主机侧端口映射（如 `17474:7474`）。

---

## 6. 数据卷管理

| 数据卷 | 挂载路径 | 用途 |
| --- | --- | --- |
| `neo4j_data` | `/data` | 图数据库数据文件（持久化） |
| `neo4j_logs` | `/logs` | Neo4j 运行日志 |

### 6.1 查看数据卷

```bash
docker volume ls | grep neo4j
```

### 6.2 清除数据（重建图谱）

```bash
# 停止服务
docker compose down

# 删除 Neo4j 数据卷（⚠️ 数据将丢失）
docker volume rm stock_helper_neo4j_data stock_helper_neo4j_logs

# 重新启动
docker compose up -d
```

---

## 7. APOC 插件

服务配置中已启用 [APOC](https://neo4j.com/labs/apoc/) 插件（`NEO4J_PLUGINS=["apoc"]`），提供批量操作、数据导入导出等增强功能。常用场景：

- `apoc.periodic.iterate`：大批量数据写入时分批提交，避免事务过大
- `apoc.create.node` / `apoc.merge.node`：动态创建/合并节点
- `apoc.export.*`：数据导出

验证 APOC 是否可用：

```cypher
RETURN apoc.version() AS version
```

---

## 8. 常见问题排查

### Q1: Neo4j 启动失败，日志报 `Invalid value for password`

Neo4j 要求密码至少 8 个字符。请检查 `.env` 中 `NEO4J_PASSWORD` 是否过短。

### Q2: app 容器无法连接 Neo4j

1. 确认 `NEO4J_URI` 使用的是服务名 `neo4j` 而非 `localhost`（容器间通信需使用 Docker 网络别名）。
2. 确认 Neo4j 容器健康检查通过：`docker compose ps` 查看 Status 列。
3. 确认两个容器在同一网络：`docker network inspect stock_helper_net`。

### Q3: Neo4j Browser 打不开（7474 端口无响应）

1. 确认容器正在运行：`docker compose ps neo4j`。
2. 检查端口是否被占用：`lsof -i :7474`。
3. 查看启动日志排查错误：`docker compose logs neo4j`。

### Q4: 数据同步后图谱为空

1. 检查同步任务日志是否有报错。
2. 在 Neo4j Browser 执行 `MATCH (n) RETURN count(n)` 确认节点数。
3. 确认 `data_engineering` 中确实有数据：通过 PostgreSQL 检查 `stock_info` 表记录数。

### Q5: 需要重置 Neo4j 密码

```bash
# 停止 Neo4j
docker compose stop neo4j

# 删除数据卷并修改 .env 中的密码
docker volume rm stock_helper_neo4j_data

# 重新启动（将使用新密码初始化）
docker compose up -d neo4j
```

---

## 9. 性能调优（可选）

对于开发环境一般无需调优。如数据量较大，可在 `docker-compose.yml` 的 `environment` 中添加：

```yaml
environment:
  - NEO4J_server_memory_heap_initial__size=512m
  - NEO4J_server_memory_heap_max__size=1G
  - NEO4J_server_memory_pagecache_size=512m
```

> 注意：Neo4j 5.x 的环境变量格式使用 `NEO4J_` 前缀 + 点号替换为下划线 + 双下划线表示实际下划线。

---

## 10. 与项目架构的关系

```
┌─────────────────────────┐
│  knowledge_center 模块   │
│  (src/modules/           │
│   knowledge_center/)     │
│                         │
│  infrastructure/        │
│    ├── neo4j_driver.py  │  ← Neo4j Driver 工厂（读取环境变量）
│    ├── graph_repository │  ← GraphRepository Port 实现
│    │   _impl.py         │
│    └── config.py        │  ← NEO4J_URI / USER / PASSWORD
└───────────┬─────────────┘
            │ Bolt (bolt://neo4j:7687)
            ▼
┌─────────────────────────┐
│  Neo4j 5 Community      │
│  (Docker Container)     │
│  端口: 7474 / 7687      │
│  数据卷: neo4j_data     │
└─────────────────────────┘
```

`knowledge_center` 模块的 Infrastructure 层负责管理 Neo4j 连接，Domain 层定义图谱模型，Application 层编排同步与查询逻辑。模块通过 `GraphRepository` 和 `GraphService` Ports 对外暴露能力，其他模块不直接访问 Neo4j。
