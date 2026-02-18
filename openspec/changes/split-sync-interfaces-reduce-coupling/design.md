## Context

当前知识图谱同步接口设计存在以下问题：

1. **单一接口承担过多职责**：`POST /knowledge-graph/sync` 同时处理股票全量、股票增量、概念同步、全部同步四种场景
2. **参数耦合度高**：请求体包含多种模式的混合参数，参数有效条件复杂（如 `target="concept"` 时忽略 `mode`、`third_codes`）
3. **易用性差**：API 不够直观，容易误用
4. **可维护性差**：路由层逻辑复杂，难以扩展新的同步类型

现有实现位置：`src/modules/knowledge_center/presentation/rest/graph_router.py`

## Goals / Non-Goals

**Goals:**
- 提供清晰、专用的同步端点，降低参数耦合度
- 保持向后兼容，原接口继续可用（标记为 deprecated）
- 改善 API 易用性和可维护性
- 为未来扩展新的同步类型奠定更好的基础

**Non-Goals:**
- 不改变 `GraphService` 层的现有方法签名
- 不改变同步的业务逻辑
- 不进行大规模重构，仅调整 Presentation 层

## Decisions

### 决策 1：新增 4 个专用同步端点

**选择**：新增 4 个专用的 REST 端点

```
POST /knowledge-graph/sync/stocks/full        # 股票全量同步
POST /knowledge-graph/sync/stocks/incremental # 股票增量同步
POST /knowledge-graph/sync/concepts            # 概念同步
POST /knowledge-graph/sync/all                 # 全部同步
```

**理由**：
- 每个端点职责单一，参数清晰
- RESTful 风格更自然
- 便于单独文档化和测试

**替代方案考虑**：
- 使用 Pydantic discriminated union：虽然可以解决类型安全问题，但仍需在一个端点内处理多种逻辑，不够直观
- 使用查询参数区分模式：参数仍然混合在一起，没有解决根本问题

### 决策 2：为每个端点创建专用的 Request DTO

**选择**：在 `graph_api_dtos.py` 中新增 4 个专用的 Request 模型

```python
class SyncStocksFullRequest(BaseModel):
    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    skip: int = Field(0, description="跳过前 N 条记录")
    limit: int = Field(10000, description="查询数量上限")

class SyncStocksIncrementalRequest(BaseModel):
    third_codes: Optional[list[str]] = Field(None, description="股票代码列表；为空时按时间窗口自动确定")
    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    window_days: int = Field(3, ge=1, description="时间窗口天数")
    limit: int = Field(10000, description="扫描数量上限")

class SyncConceptsRequest(BaseModel):
    batch_size: int = Field(500, description="批量大小")

class SyncAllRequest(BaseModel):
    mode: Literal["full", "incremental"] = Field(..., description="股票同步模式")
    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    # 其他必要字段...
```

**理由**：
- 每个 DTO 只包含该端点真正需要的参数
- 类型安全，自动文档更清晰
- 便于未来扩展各自的特有参数

### 决策 3：保留原接口并标记为 deprecated

**选择**：保留 `POST /knowledge-graph/sync` 接口，内部将请求转发到新的专用端点处理逻辑，并在响应头或文档中标记为 deprecated

**理由**：
- 保证向后兼容性，避免破坏现有客户端
- 给用户充足的迁移时间
- 可以在未来的大版本中彻底移除

**迁移策略**：
- 在 OpenAPI 文档中标记原接口为 deprecated
- 在日志中记录 deprecated 接口的使用
- 建议用户迁移到新接口

## Risks / Trade-offs

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 客户端仍在使用旧接口 | 中 | 高 | 保留旧接口，标记 deprecated，提供迁移指南 |
| 新增接口导致 API 表面增大 | 低 | 中 | 通过清晰的分组和文档化缓解 |
| 路由层代码重复 | 低 | 中 | 提取公共处理逻辑到私有辅助函数 |

## Migration Plan

1. **阶段 1**：新增专用 Request DTO 和路由端点
2. **阶段 2**：实现新端点的处理逻辑（复用现有的 GraphService 调用）
3. **阶段 3**：修改原接口，标记 deprecated，内部转发到新逻辑
4. **阶段 4**：更新 API 文档，推荐使用新接口
5. **阶段 5**：监控旧接口使用情况，在未来版本中考虑移除

## Open Questions

无 - 设计方案已明确。
