# CI/CD 配置说明

## 概述

本项目使用 GitHub Actions 实现持续集成和持续部署（CI/CD）。

## 目录结构

```
.github/workflows/
├── ci.yml    # 持续集成配置
└── cd.yml    # 持续部署配置
```

## CI 配置（ci.yml）

### 触发条件
- 推送到 `main` 分支
- 针对 `main` 分支的 Pull Request

### 工作流程

#### 1. Quality Job（代码质量检查）
- **运行环境**: Ubuntu latest, Python 3.10
- **检查项**:
  - ✅ flake8 - 代码风格检查
  - ✅ black --check - 代码格式化检查
  - ✅ isort --check-only - 导入排序检查

#### 2. Test Job（测试）
- **运行环境**: Ubuntu latest, Python 3.10
- **服务依赖**: PostgreSQL 15 (测试数据库)
- **执行步骤**:
  1. 安装项目依赖
  2. 运行 pytest 测试套件
  3. 生成覆盖率报告（XML + 终端输出）
  4. 上传覆盖率报告到 GitHub Artifacts

### 环境变量配置
```yaml
POSTGRES_SERVER: localhost
POSTGRES_USER: postgres
POSTGRES_PASSWORD: password
POSTGRES_DB: stock_helper_test
POSTGRES_PORT: 5432
ENVIRONMENT: test
PYTHONPATH: ${{ github.workspace }}/src
```

## CD 配置（cd.yml）

### 触发条件
- 推送到 `main` 分支
- 创建版本标签（如 `v1.0.0`）
- 手动触发（workflow_dispatch）

### 工作流程

#### 1. Build and Push Job（构建并推送 Docker 镜像）
- **运行环境**: Ubuntu latest
- **功能**:
  - 使用 Docker Buildx 构建镜像
  - 推送到 GitHub Container Registry (ghcr.io)
  - 支持多标签策略：
    - 分支名
    - PR 号
    - SemVer 版本
    - SHA 哈希
    - latest（main 分支）

- **镜像命名**: `ghcr.io/{owner}/{repo}`

#### 2. Deploy Job（部署到生产环境）
- **依赖**: build-and-push job 成功后执行
- **条件**: 仅当推送到 main 分支时
- **环境**: production（需要在 GitHub 配置）
- **功能**: 占位符，需要根据实际部署环境配置

### 配置部署环境

在 GitHub 仓库中配置生产环境：

1. 进入 `Settings` > `Environments`
2. 添加新环境 `production`
3. 配置环境变量：
   - `DEPLOYMENT_URL`: 生产环境 URL
4. 配置 Secrets（如需要）:
   - 部署令牌
   - API 密钥
   - 服务器凭证

## 本地测试 CI/CD

### 运行代码质量检查
```bash
# flake8
flake8 src tests

# black
black --check src tests

# isort
isort --check-only src tests
```

### 运行测试
```bash
# 本地运行测试（需要 PostgreSQL）
pytest tests/ -v --cov=src --cov-report=term-missing
```

### 构建 Docker 镜像
```bash
# 构建
docker build -t stock_helper:latest .

# 运行
docker-compose up -d
```

## 故障排查

### CI 失败常见原因

1. **flake8 错误**
   - 运行 `flake8 src tests` 查看具体错误
   - 使用 `black` 和 `isort` 自动格式化代码

2. **测试失败**
   - 检查测试日志
   - 确保数据库连接配置正确
   - 检查测试数据依赖

3. **Docker 构建失败**
   - 检查 Dockerfile 语法
   - 确保 requirements.txt 完整
   - 验证基础镜像可用性

### CD 失败常见原因

1. **认证失败**
   - 检查 GITHUB_TOKEN 权限
   - 确认 packages 写入权限已启用

2. **部署失败**
   - 验证环境变量配置
   - 检查部署脚本权限
   - 确认目标服务器可访问

## 最佳实践

1. **代码提交前**
   - 运行所有本地检查
   - 确保测试通过
   - 检查代码覆盖率

2. **Pull Request**
   - 等待 CI 全部通过
   - 审查代码质量报告
   - 确保覆盖率不下降

3. **生产部署**
   - 使用版本标签触发
   - 配置部署审批流程
   - 监控部署状态

## 后续改进

- [ ] 集成代码覆盖率服务（如 Codecov）
- [ ] 添加自动化 E2E 测试
- [ ] 配置多环境部署（staging, production）
- [ ] 添加部署通知（Slack, Discord）
- [ ] 实现蓝绿部署或金丝雀发布
- [ ] 添加性能测试步骤
