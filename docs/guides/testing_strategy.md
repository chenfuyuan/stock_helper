# 项目测试策略与目录结构指南

本文档旨在为项目建立一个清晰、健壮、可维护的测试结构，以确保代码质量和未来的可维护性。

## 核心理念：测试金字塔 (Testing Pyramid)

我们遵循经典的测试金字塔模型来组织测试。该模型将测试分为三个主要层次：

```
      ▲
     / 
    /   \      E2E 测试 (End-to-End)
   /-----\     (端到端) - 少而精，覆盖关键流程
  /       
 /---------\   集成测试 (Integration)
/           \  (服务间) - 数量适中，验证组件交互
/-------------
单元测试 (Unit)
(逻辑单元) - 量大而快，保证基础逻辑正确
```

- **单元测试 (Unit Tests)**: 构成金字塔的坚实底座，数量最多，运行最快。
- **集成测试 (Integration Tests)**: 位于中间层，验证模块与数据库、外部API等组件的交互。
- **端到端测试 (E2E Tests)**: 位于顶层，数量最少，运行最慢，但覆盖完整的用户场景。

## 建议的 `tests` 目录结构

基于测试金字塔模型和本项目的技术栈（FastAPI, SQLAlchemy, 多模块结构），规划 `tests` 目录如下：

```
tests/
├── __init__.py
│
├── conftest.py          # 👈 全局的 Pytest Fixtures (数据库连接, TestClient 等)
│
├── unit/                # 单元测试 (隔离、快速，不依赖外部服务)
│   │
│   ├── modules/         #   与 src/modules/ 结构镜像
│   │   ├── knowledge_center/
│   │   │   ├── test_domain_models.py      #   测试领域模型的业务逻辑
│   │   │   └── test_application_services.py #   测试应用服务，但 mock 掉仓储库
│   │   ├── market_insight/
│   │   │   └── test_concept_heat_calculator.py # 测试纯计算逻辑
│   │   └── ...
│   │
│   └── shared/
│       └── test_dtos.py         #   测试 DTO 的校验逻辑
│
├── integration/         # 集成测试 (测试组件间的交互)
│   │
│   ├── modules/         #   与 src/modules/ 结构镜像
│   │   ├── knowledge_center/
│   │   │   ├── test_pg_repositories.py    #   【重要】测试仓储库与真实 PG 数据库的交互
│   │   │   └── test_neo4j_repositories.py #   【重要】测试仓储库与真实 Neo4j 的交互
│   │   └── ...
│   │
│   └── test_main_container.py   #   测试主 DI 容器的装配是否正确
│
└── e2e/                   # 端到端测试 (从 API 入口到数据库落地的完整流程)
    │
    ├── test_health_api.py       #   测试 /health 端点
    └── test_concept_relation_api.py # 模拟 HTTP 请求，验证完整的 CRUD 流程
```

## 各层级详解

### 1. `tests/unit` (单元测试)

- **目的**: 验证最小的代码单元（单个函数、类、方法）的逻辑是否正确。
- **原则**: **快、隔离**。绝不连接真实的数据库、文件系统或网络。所有外部依赖（如 Repository、LLMService）都必须被 **Mock** 掉。
- **工具**: `pytest` + Python 内置的 `unittest.mock`。
- **价值**: 这是最大量的测试。它们运行速度极快，能为你的日常开发提供即时反馈，是 TDD（测试驱动开发）的基石。

### 2. `tests/integration` (集成测试)

- **目的**: 验证你的代码和外部组件（数据库、缓存、第三方 API）的集成是否正确。
- **原则**: **真实交互**。这是你测试数据库查询语句、ORM 映射、DI 容器配置是否正确的最佳位置。
- **工具**: `pytest` + `testcontainers` (如果用 Docker 启动数据库) + `Alembic` (管理测试数据库的 schema)。`conftest.py` 在这里至关重要，用来管理测试数据库的连接和清理。
- **价值**: 给你信心，确保你的代码与外部世界的“契约”是有效的。例如，`PgConceptRelationRepository` 的实现是否能正确地在 PostgreSQL 中增删改查。

### 3. `tests/e2e` (端到端测试)

- **目的**: 模拟真实用户的操作，从系统的入口（如一个 HTTP API 请求）一直贯穿到最终结果（如数据库中出现一条记录，或返回一个特定的 JSON 响应）。
- **原则**: **黑盒视角**。不关心内部实现，只关心输入和输出。
- **工具**: FastAPI 的 `TestClient` + `pytest`。
- **价值**: 提供最高层次的信心，确保整个系统作为一个整体是工作的。但它们运行最慢，也最脆弱（一个小的改动可能破坏很多 E2E 测试），所以数量应该最少，只覆盖最核心的用户流程。

## 后续实施建议

1.  **从 `integration` 测试开始**: 对于一个已有代码的项目，先为你的 Repository（仓储库）编写集成测试，确保数据持久化层是可靠的。这能以最快速度获得最大回报。
2.  **补全 `unit` 测试**: 接着，为核心的领域服务和复杂的业务逻辑函数编写单元测试。
3.  **最后添加 `e2e` 测试**: 为最关键的几个 API 流程（例如，用户注册、创建核心资源）编写端到端测试，确保核心用户路径的正确性。
4.  **利用 `conftest.py`**: 将所有测试共享的设置（如数据库连接、FastAPI `TestClient` 实例、数据工厂函数）都放在 `conftest.py` 中，以 Fixture 的形式提供给测试函数，保持测试代码的整洁。
5.  **使用 Pytest Markers**: 为不同类型的测试打上标记（`@pytest.mark.unit`, `@pytest.mark.integration`），这样可以分类别运行测试，例如在本地开发时只运行快速的单元测试。
