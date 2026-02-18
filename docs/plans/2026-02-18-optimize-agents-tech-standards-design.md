# 优化 AGENTS.md 和 tech-standards.md 设计文档

**日期：** 2026-02-18  
**作者：** AI Assistant  
**状态：** 设计完成，待实现

---

## 1. 背景与目标

### 1.1 背景
当前项目中有两个关键文档：
- `AGENTS.md`：根目录的代理指令文档
- `tech-standards.md`：`openspec/specs/` 下的技术规范文档

两个文档存在内容重叠、职责不清的问题。

### 1.2 目标
- 明确两个文档的职责划分
- 提高文档的清晰度和可读性
- 简化复杂表述
- 保持架构一致性

---

## 2. 设计方案

### 2.1 文档职责划分

| 文档 | 定位 | 目标读者 |
|------|------|---------|
| `AGENTS.md` | AI 代理导航卡片 | AI 助手 |
| `tech-standards.md` | 完整技术规范手册 | AI 助手 + 开发者 |

### 2.2 AGENTS.md 新结构

```
# Agent Instructions — Stock Helper

**角色：** Senior Python Architect（一句话定位）
**原则：** DDD、Clean Architecture、SOLID
**目标：** High cohesion, low coupling, maintainable code

---

## 文档地图（必读）

| 场景 | 查阅文档 |
|------|---------|
| 模块归属、边界、依赖 | [openspec/specs/vision-and-modules.md](openspec/specs/vision-and-modules.md) |
| 技术栈、完整规范、响应流程 | [openspec/specs/tech-standards.md](openspec/specs/tech-standards.md) |

---

## 核心原则（精简）

1. **DDD First**：领域与基础设施解耦，模块通过 Ports 通信
2. **依赖倒置**：依赖抽象而非实现
3. **代码整洁**：强制类型注解、无魔数、短函数单职责
4. **全局视角**：每次改动考虑架构一致性

---

## 响应流程（3步）

1. **架构分析** → 2. **代码设计** → 3. **重构建议**

**Quick Fix 例外**：用户标注「Quick Fix」「Script Only」或 trivial 修改时，直接修正。

---

## 语言约定

- 解释用 **中文（简体）**
- 代码命名用英文，注释和 Docstring 必须用中文
```

### 2.3 tech-standards.md 新结构

```
# 技术规范与 AI 响应协议（Source of Truth）

**用途**：本文档是代码风格、技术栈与 AI 响应流程的单一事实来源。
**与 AGENTS.md 的关系**：AGENTS.md 是精简入口，本文档是完整细则。

---

## 0. 文档导航

- AGENTS.md（入口）→ 本文档（详情）
- 本文档与 vision-and-modules.md 配合使用

---

## 1. 角色与配置

## 2. 核心哲学（详细）

## 3. 技术栈与标准

## 4. 文件与模块命名规范

## 5. DTO 与 Port 组织规范

## 6. 模块内部结构（含目录模板）

## 7. 领域建模约定

## 8. 异常处理规范

## 9. 日志规范

## 10. 响应协议（完整流程）

## 11. 例外规则

## 12. 语气与语言约定

## 13. 检查清单（新增）
```

---

## 3. 实现要点

### 3.1 AGENTS.md 改动
- 删除技术栈细节、目录结构、文件规范等内容
- 只保留角色、文档地图、核心原则（4条）、响应流程（3步）
- 所有详情都指向 tech-standards.md

### 3.2 tech-standards.md 改动
- 在开头增加「文档导航」章节，明确与 AGENTS.md 的关系
- 增加「检查清单」章节，让规范可操作
- 优化表述，简化复杂句子
- 保持技术细节完整性

---

## 4. 验收标准

- [ ] AGENTS.md 简洁明了，一页内可看完
- [ ] 两个文档职责清晰，无内容冲突
- [ ] 文档间交叉引用正确
- [ ] 语言表述简化，更易理解
