# CI/CD 配置与代码质量标准

**用途**：定义项目的持续集成流程、代码质量检查标准和自动化工具配置，确保团队开发一致性和代码质量。

---

## CI/CD 流水线架构

### 环境配置

- **运行环境**：Ubuntu Latest
- **Python版本**：3.10+
- **数据库**：PostgreSQL 15-Alpine（测试环境）
- **依赖管理**：pip + requirements.txt

### 流水线阶段

```yaml
# .github/workflows/ci.yml 核心结构
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10"]
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
          POSTGRES_DB: stock_helper_test
        ports:
          - 5432:5432
```

---

## 代码质量检查工具链

### 1. 静态代码分析

#### flake8 配置
```ini
[flake8]
max-line-length = 79
exclude = 
    .git,
    __pycache__,
    .mypy_cache,
    .pytest_cache,
    .venv,
    venv
ignore = 
    E203,  # whitespace before ':'
    W503   # line break before binary operator
```

#### mypy 配置
```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
ignore_missing_imports = True
```

### 2. 代码格式化工具

#### black 配置
```toml
[tool.black]
line-length = 79
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

#### isort 配置
```toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 79
known_first_party = ["src"]
```

---

## 自动化修复流程

### 预提交钩子配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pycqa/autoflake
    rev: v2.3.1
    hooks:
      - id: autoflake
        args:
          - --in-place
          - --remove-all-unused-imports
          - --remove-unused-variables
          - --remove-duplicate-keys

  - repo: https://github.com/pycqa/isort
    rev: 6.1.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/psf/black
    rev: 25.9.0
    hooks:
      - id: black
        language_version: python3
```

### 批量修复脚本

```bash
#!/bin/bash
# scripts/fix_code_quality.sh

echo "🔧 开始自动修复代码质量问题..."

# 1. 清理未使用的导入和变量
echo "📦 清理未使用的导入..."
find src/ tests/ -name "*.py" -exec autoflake \
  --in-place \
  --remove-all-unused-imports \
  --remove-unused-variables \
  --remove-duplicate-keys {} \;

# 2. 规范化导入顺序
echo "📚 规范化导入顺序..."
isort src/ tests/ --profile black

# 3. 格式化代码
echo "✨ 格式化代码..."
black src/ tests/ --line-length 79

# 4. 清理空白行
echo "🧹 清理空白行..."
find src/ tests/ -name "*.py" -exec sed -i '' 's/ *$//' {} \;

echo "✅ 代码质量修复完成！"
```

### E501行长度问题专项修复

基于实际修复经验，以下是常见的E501问题及修复模式：

#### 1. 导入语句过长修复

```python
# 问题示例（85字符）：
from src.modules.research.infrastructure.financial_snapshot.snapshot_builder import (
    FinancialSnapshotBuilderImpl,
)

# 修复后：
from src.modules.research.infrastructure.\
        financial_snapshot.snapshot_builder import (
            FinancialSnapshotBuilderImpl,
        )
```

**修复要点**：
- 使用反斜杠(`\`)在合适位置换行
- continuation line 缩进4个空格
- 括号内内容缩进8个空格

#### 2. JSON字符串过长修复

```python
# 问题示例（164字符）：
valid_json = '{"signal":"BEARISH","confidence":0.6,"summary_reasoning":"RSI 超买","key_technical_levels":{"support":9.0,"resistance":12.0},"risk_warning":"跌破支撑"}'

# 修复后：
valid_json = (
    '{"signal":"BEARISH","confidence":0.6,'
    '"summary_reasoning":"RSI 超买",'
    '"key_technical_levels":{"support":9.0,"resistance":12.0},'
    '"risk_warning":"跌破支撑"}'
)
```

**修复要点**：
- 使用括号包裹整个字符串
- 按逻辑结构换行（如JSON字段）
- 每行末尾加逗号（除最后一行）

#### 3. 手动修复命令

```bash
# 检查具体的E501错误
flake8 --select=E501 src tests

# 针对特定文件修复
flake8 --select=E501 tests/research/infrastructure/test_*.py

# 验证修复效果
flake8 src tests --max-line-length=79
```

#### 4. 历史修复案例

以下文件曾出现E501问题并已修复，可作为参考：
- `tests/research/infrastructure/test_financial_snapshot_builder.py:11` - 导入语句过长
- `tests/research/infrastructure/test_indicator_calculator_adapter.py:9` - 导入语句过长
- `tests/research/infrastructure/test_technical_analyst_agent_adapter.py:18,27` - 导入语句和JSON字符串过长
- `tests/research/infrastructure/test_valuation_snapshot_builder.py:17` - 导入语句过长

---

## 质量门禁标准

### 错误阈值

| 检查工具 | 当前状态 | 目标阈值 | 严重程度 |
|---------|---------|---------|---------|
| flake8  | < 100   | < 50    | 中等     |
| mypy    | < 50    | < 20    | 严重     |
| 测试覆盖率 | > 70%  | > 85%   | 严重     |
| E501行长度 | < 344  | < 50    | **警告** |

### 阻塞性问题

以下问题会**阻止**合并：

1. **mypy严重错误**：
   - 缺失类型注解的核心函数
   - 异步函数接口不一致
   - 类型不匹配的赋值操作

2. **flake8阻塞性错误**：
   - 导入错误（未定义的名称）
   - 语法错误
   - 大量未使用的导入（> 20个）

3. **测试失败**：
   - 核心业务逻辑测试失败
   - 集成测试环境问题

### 警告性问题

以下问题会发出警告但**不阻止**合并：

1. **E501行长度违规**（当前344个，目标<50个）
2. **空白行格式问题**
3. **非核心函数的类型注解缺失**
4. **文档字符串缺失**

---

## CI优化策略

### 并行执行

```yaml
# 并行运行检查以加速CI
- name: Run checks in parallel
  run: |
    python -m flake8 src tests &
    python -m mypy src --ignore-missing-imports &
    wait
```

### 缓存策略

```yaml
# 缓存依赖以加速CI
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### 测试环境优化

```yaml
# 使用Docker Compose确保环境一致性
- name: Start test environment
  run: |
    docker compose -f docker-compose.test.yml up -d
    docker compose exec -T app pytest tests/
```

---

## 本地开发规范

### 提交前检查

```bash
# 本地运行完整检查
make check-quality

# 等价于：
python -m flake8 src tests
python -m mypy src --ignore-missing-imports
pytest tests/ --cov=src

# E501专项检查（必须为零）
python -m flake8 --select=E501 src tests
if [ $? -ne 0 ]; then
    echo "❌ 发现行长度违规，请修复后再提交"
    echo "💡 参考 openspec/specs/ci-standards.md 中的修复指南"
    exit 1
fi

# 验证修复效果
python -m flake8 src tests --max-line-length=79
echo "✅ 所有检查通过，可以提交"
```

### 提交前检查清单

- [ ] 运行 `flake8 src tests --max-line-length=79` 无E501错误
- [ ] 运行 `mypy src tests --ignore-missing-imports` 无关键错误
- [ ] 运行 `pytest tests/` 所有测试通过
- [ ] 检查导入语句格式符合规范（使用反斜杠换行）
- [ ] 检查长字符串已正确换行（使用括号包裹）
- [ ] 确认代码无未使用的导入
- [ ] 验证E501专项检查通过（零容忍）

### IDE配置

#### VS Code settings.json
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm配置
- 启用Black作为代码格式化工具
- 配置isort作为导入优化工具
- 启用mypy类型检查
- 设置行长度为79字符

---

## 持续改进机制

### 定期审查

- **每月**：审查错误趋势和工具版本更新
- **每季度**：评估质量门禁阈值的合理性
- **每半年**：全面审查CI/CD流程效率

### 团队培训

- **新成员入职**：CI/CD流程和代码质量标准培训
- **技术分享**：定期分享代码质量最佳实践
- **工具更新**：及时同步新工具和配置变更

### 反馈循环

- **CI失败通知**：及时通知相关开发者
- **质量报告**：每周生成代码质量报告
- **改进建议**：收集团队反馈持续优化流程

---

## 故障排查指南

### 常见CI问题

1. **数据库连接失败**
   ```bash
   # 检查数据库服务状态
   docker compose ps
   
   # 重启数据库服务
   docker compose restart postgres
   ```

2. **依赖安装失败**
   ```bash
   # 清理pip缓存
   pip cache purge
   
   # 重新安装依赖
   pip install -r requirements.txt --force-reinstall
   ```

3. **类型检查错误**
   ```bash
   # 详细查看mypy错误
   python -m mypy src --show-error-codes --show-error-context
   ```

### 性能优化

- **并行测试**：使用pytest-xdist并行运行测试
- **增量检查**：仅检查变更的文件
- **智能缓存**：基于文件哈希的智能缓存策略

---

*此文档与`.github/workflows/ci.yml`、`pyproject.toml`、`.pre-commit-config.yaml`等配置文件保持同步更新。*
