# CI/CD 配置与代码质量标准

**用途**：定义项目的持续集成流程、代码质量检查标准和自动化工具配置，确保团队开发一致性和代码质量。

---

## 核心原则

1.  **单一事实来源**：所有工具配置（Line Length, Ignore Rules）尽可能统一在 `pyproject.toml` 中管理，避免 CLI 参数硬编码。
2.  **自动化优先**：凡是能自动修复的问题（Formatting, Imports），绝不消耗人工 Review 时间。
3.  **安全左移**：在提交阶段即拦截已知漏洞和敏感信息泄漏。

---

## CI/CD 流水线架构

### 环境配置

-   **运行环境**：Ubuntu Latest
-   **Python版本**：3.10+
-   **数据库**：PostgreSQL 15-Alpine（测试环境）
-   **依赖管理**：pip + requirements.txt (配合 pip-audit 检查)

### 流水线阶段

流水线定义在 `.github/workflows/ci.yml` 中，包含以下核心作业：

1.  **Lint & Security** (并行执行):
    -   Code Style (Flake8, Black, Isort)
    -   Type Check (Mypy)
    -   Security Scan (Bandit)
    -   Dependency Audit (Pip-audit)
2.  **Test**:
    -   Unit Tests
    -   Integration Tests (with Docker Services: Postgres, Neo4j)

---

## 代码质量检查工具链

### 1. 静态代码分析 & 格式化

所有配置主要依据 `pyproject.toml`。

| 工具 | 用途 | 关键配置 |
| :--- | :--- | :--- |
| **Black** | 代码格式化 | `line-length = 100` |
| **Isort** | 导入排序 | `profile = "black"`, `line_length = 100` |
| **Flake8** | 风格检查 | `max-line-length = 100`, `exclude = .venv,...` |
| **Mypy** | 类型检查 | `ignore_missing_imports = true` |
| **Autoflake**| 清理冗余 | 移除未使用导入与变量 |

#### 统一行长度标准：100 字符

项目统一采用 **100 字符** 行长度限制（与 `pyproject.toml` 保持一致），以适应现代显示器并减少不必要的换行。

### 2. 安全扫描（新增）

-   **Bandit**：扫描 Python 代码中的常见安全漏洞（如硬编码密码、SQL 注入风险）。
    ```bash
    bandit -r src/ -c pyproject.toml
    ```
-   **Pip-audit**：扫描依赖包是否存在已知 CVE 漏洞。
    ```bash
    pip-audit -r requirements.txt
    ```

---

## 自动化修复流程

### 预提交钩子 (Pre-commit)

推荐安装 `pre-commit` 以在本地提交时自动修复格式问题：

```yaml
# .pre-commit-config.yaml 摘要
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

### 批量修复脚本

如果未使用 pre-commit，可使用以下脚本一键修复所有格式问题：

```bash
#!/bin/bash
# scripts/fix_code_quality.sh

echo "🔧 开始自动修复代码质量问题..."

# 1. 清理未使用的导入和变量
echo "📦 清理未使用的导入..."
autoflake --in-place --recursive --remove-all-unused-imports --remove-unused-variables src/ tests/

# 2. 规范化导入顺序 (读取 pyproject.toml 配置)
echo "📚 规范化导入顺序..."
isort src/ tests/

# 3. 格式化代码 (读取 pyproject.toml 配置)
echo "✨ 格式化代码..."
black src/ tests/

echo "✅ 代码质量修复完成！"
```

---

## 本地开发规范

### 常用命令

由 `Makefile` 提供快捷入口，参数均从配置文件读取，**无需手动指定行长度**：

```bash
# 运行完整质量检查 (Lint + Test)
make check-quality

# 仅运行 Lint (Flake8, Mypy)
make lint

# 自动修复格式问题
make fix-quality

# 运行测试
make test
```

### IDE 配置建议

#### VS Code `settings.json`

```json
{
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "python.sortImports.args": ["--profile", "black", "--line-length", "100"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.analysis.typeCheckingMode": "basic"
}
```

---

## 质量门禁标准

### 阻塞性指标 (Blockers)

以下任何一项失败，PR 均不可合并：

1.  **CI 构建失败**：任何步骤（Lint, Test, Docker Build）非零退出。
2.  **关键类型错误**：Mypy 检查出的错误。
3.  **测试失败**：任何单元测试或集成测试失败。
4.  **安全高危漏洞**：Bandit 发现 High Severity 问题。
5.  **依赖漏洞**：Pip-audit 发现已修复的 CVE。

### 告警性指标 (Warnings)

-   **测试覆盖率**：核心模块应 > 80%。
-   **函数复杂度**：单个函数不超过 15 行逻辑代码（建议值）。

---

## 持续改进与反馈

1.  **定期更新**：每月检查一次 `pre-commit` hook 和依赖包更新。
2.  **例外处理**：如果某行必须超过 100 字符（如长 URL），使用 `# noqa: E501` 豁免，但需尽量避免。
3.  **配置调整**：如需修改检查规则，必须通过 PR 修改 `pyproject.toml`，禁止在命令中临时覆盖。

---

*此文档与 `pyproject.toml` 及 `.github/workflows/` 保持同步。*
