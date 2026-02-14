# OpenSpec 标准操作流程（SOP）

> **适用范围**：本项目所有需求变更、新功能开发、重构优化均通过 OpenSpec 工作流管理。本文档描述从需求提出到归档的完整操作流程。

---

## 1. 概述

OpenSpec 是一套 **spec-driven（规格驱动）** 的变更管理工作流。核心理念：

- **先规格后实现**：每次变更在动手写代码前，先通过结构化的产出物（Proposal → Spec → Design → Tasks）明确"做什么"和"怎么做"。
- **可验证**：每个 Spec 中的 Scenario（WHEN/THEN）在交付时必须有对应的自动化测试。
- **可追溯**：所有变更通过 `openspec/changes/` 目录管理，完成后归档到 `archive/`，形成完整的决策审计链。

---

## 2. 关键目录结构

```
openspec/
├── config.yaml                      # 项目上下文（创建 change 时自动注入）
├── specs/                           # 主规格目录（Source of Truth）
│   ├── README.md                    # 全景导航索引（新人入口）
│   ├── vision-and-modules.md        # 模块边界与架构（Source of Truth）
│   ├── tech-standards.md            # 技术规范与 AI 响应协议
│   └── <feature-name>/spec.md       # 各能力的规格文件
└── changes/                         # 变更管理
    ├── <change-id>/                 # 进行中的变更
    │   ├── proposal.md              # 提案
    │   ├── spec.md                  # 规格（delta spec）
    │   ├── design.md                # 设计方案
    │   └── tasks.md                 # 实现任务清单
    └── archive/                     # 已归档的变更
        └── <date>-<change-name>/    # 按日期归档
```

---

## 3. 完整工作流（6 步）

### 步骤 1：探索与澄清（Explore）

**何时用**：需求不明确、想先调研可行性、或需要讨论方案取舍时。

**操作**：使用 `/opsx-explore` 命令进入探索模式。

**输出**：明确的需求描述、边界约束、非目标。

**提示**：
- 探索阶段不产出正式文档，是自由讨论。
- 如果需求已经很清晰，可以跳过直接进入步骤 2。

---

### 步骤 2：创建变更（New Change）

**操作**：使用 `/opsx-new` 命令，描述变更目标。

**产出**：`openspec/changes/<change-id>/proposal.md`

**Proposal 内容**：
- **变更目标**：一句话说明这个变更解决什么问题
- **变更内容**：具体做什么
- **影响范围**：涉及哪些模块、哪些 Bounded Context
- **非目标**：明确不做什么
- **可验证性**：如何通过自动化测试验证

**检查项**：
- [ ] 变更归属到正确的 Bounded Context（参考 `vision-and-modules.md`）
- [ ] 未跨边界堆逻辑
- [ ] 明确了测试验证方式

---

### 步骤 3：逐步推进产出物（Continue）

**操作**：使用 `/opsx-continue` 命令，系统会自动判断下一个需要创建的产出物。

**产出物顺序**：`proposal.md` → `spec.md` → `design.md` → `tasks.md`

| 产出物 | 内容 | 关键要求 |
|--------|------|---------|
| **proposal.md** | 提案 | 清晰的目标、边界、非目标 |
| **spec.md** | 规格（delta spec） | 每个 Requirement 含 WHEN/THEN Scenario；遵循 SHALL/SHALL NOT 语义 |
| **design.md** | 设计方案 | 类/接口签名、数据流、依赖关系；符合 DDD 四层 |
| **tasks.md** | 实现任务清单 | 每个任务 ≤ 2 小时；归属到单一 Bounded Context |

**快捷方式**：如果需求简单且你想一次性生成所有产出物，使用 `/opsx-ff`（Fast Forward）。

**提示**：
- 每步产出后，AI 会等待你审核确认，再进入下一步。
- 对产出物有修改意见时直接提出，AI 会先做合理性分析再决定是否采纳（参见 `tech-standards.md § OpenSpec: 评审用户提出的修改建议`）。

---

### 步骤 4：实现（Apply）

**操作**：使用 `/opsx-apply` 命令，AI 会按 `tasks.md` 中的任务逐个实现。

**关键规则**：
- 实现时必须遵循 `tech-standards.md` 中的代码规范
- 新代码必须落在 `vision-and-modules.md § 4 目录映射` 对应的路径下
- 跨模块调用必须通过被调用模块的 Application 接口
- Domain 层不 import 其他模块的任何类型

**测试约定**：
- Spec 中每个 Scenario 在交付时须有对应的自动化测试
- 实现顺序灵活（可先实现再补测），以完整测试通过为完成标准
- 测试执行使用 `docker compose exec app pytest`（运行时验证）

---

### 步骤 5：验证（Verify）

**操作**：使用 `/opsx-verify` 命令，AI 会对照 change 的 spec 逐条验证实现是否完整。

**验证内容**：
- 每个 Requirement 的每个 Scenario 是否有对应实现
- 每个 Scenario 是否有对应测试
- 代码是否符合架构约束（分层、Port 通信、无跨模块直接依赖）
- 测试是否通过

**验证策略**（参见 `tech-standards.md § 验证环境与工具`）：
- **运行时验证**（pytest、python -c）：必须使用 `docker compose exec app <command>`
- **静态分析**（grep、find、ls）：使用本地命令

---

### 步骤 6：同步与归档（Sync + Archive）

**同步 Spec**：使用 `/opsx-sync` 将 delta spec 合并到主 spec 目录 `openspec/specs/<feature>/spec.md`。

**归档变更**：使用 `/opsx-archive` 将已完成的 change 移入 `openspec/changes/archive/<date>-<name>/`。

**批量归档**：如果有多个并行完成的 change，使用 `/opsx-bulk-archive`。

---

## 4. 流程总结图

```
  需求/问题
     │
     ▼
  ┌──────────────┐
  │  /opsx-explore │ ← 可选：需求不清晰时先探索
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  /opsx-new    │ → 创建 proposal.md
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ /opsx-continue│ → spec.md → design.md → tasks.md
  │  或 /opsx-ff  │   （逐步推进 或 一次性快进）
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  /opsx-apply  │ → 按 tasks 逐个实现 + 补测
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ /opsx-verify  │ → 对照 spec 验证实现完整性
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  /opsx-sync   │ → delta spec 合并到主 specs
  │ /opsx-archive │ → change 归档
  └──────────────┘
```

---

## 5. 常用命令速查

| 命令 | 用途 | 何时用 |
|------|------|--------|
| `/opsx-explore` | 进入探索模式 | 需求不清晰、想讨论方案时 |
| `/opsx-new` | 创建新变更 | 明确要做什么后 |
| `/opsx-continue` | 推进下一个产出物 | 逐步创建 spec/design/tasks |
| `/opsx-ff` | 快进创建全部产出物 | 需求简单、想快速开始实现 |
| `/opsx-apply` | 实现任务 | 所有产出物就绪后 |
| `/opsx-verify` | 验证实现 | 实现完成后、归档前 |
| `/opsx-sync` | 同步 delta spec 到主 specs | 验证通过后 |
| `/opsx-archive` | 归档已完成的变更 | 同步完成后 |
| `/opsx-bulk-archive` | 批量归档 | 多个变更同时完成 |
| `/opsx-onboard` | 引导式上手 | 第一次使用 OpenSpec |

---

## 6. 最佳实践

### 6.1 变更粒度

- **一个 change 解决一个问题**：避免在同一个 change 中混合不相关的需求。
- **任务粒度 ≤ 2 小时**：如果单个 task 超过 2 小时，考虑拆分。
- **一个 task 归属一个 Bounded Context**：避免跨模块的大任务。

### 6.2 Spec 编写规范

- 使用 **SHALL / SHALL NOT** 表达强制要求。
- 每个 Requirement 至少包含一个 **Scenario**（WHEN/THEN 格式）。
- Scenario 应覆盖：正常路径、边界条件、错误处理。
- **禁止含糊表述**：如"系统应合理处理"→ 改为明确的 SHALL 行为。

### 6.3 与架构规范的关系

- **开始前**：先查阅 `vision-and-modules.md` 确认变更归属的 Bounded Context。
- **设计时**：遵循 `tech-standards.md` 的分层规则和命名约定。
- **实现时**：代码路径必须与 `vision-and-modules.md § 4 目录映射` 一致。
- **如需修改架构规范**：在 change 的 proposal 中明确说明，AI 会做合理性分析后决定是否采纳。

### 6.4 测试策略

- Spec 中的 Scenario 是**验收测试的蓝本**——每个 WHEN/THEN 对应至少一个测试用例。
- 优先通过 **Mock Port** 进行单元测试（无需真实 LLM/DB）。
- 集成测试使用 Docker 环境（`docker compose exec app pytest`）。
- 实现与测试的顺序灵活，但**交付时所有测试必须通过**。

---

## 7. 常见问题

### Q: 紧急修复（hotfix）也需要走完整流程吗？

**不需要**。如果是 Quick Fix（拼写错误、一行修复等），在提交信息中标注 `Quick Fix` 即可，不需要创建 change。参见 `tech-standards.md § 例外规则`。

### Q: 发现已有 spec 需要修改怎么办？

创建一个新的 change，在 proposal 中说明需要修改哪个 spec 的哪个 Requirement，以及修改原因。spec 中使用 `MODIFIED` 或 `REMOVED` 标记（与 `ADDED` 对应）。

### Q: 多人同时进行不同的 change 会冲突吗？

只要各 change 归属不同的 Bounded Context 就不会冲突。如果涉及同一模块，建议在 proposal 阶段协调。

### Q: 如何查看历史变更？

浏览 `openspec/changes/archive/` 目录，每个子目录对应一个已完成的变更，包含完整的 proposal/spec/design/tasks。
