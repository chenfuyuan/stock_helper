## Context

Knowledge Center MVP 已建立基础股票元数据图谱（Stock → Industry/Area/Market/Exchange），所有数据通过 `data_engineering` 模块从 Tushare 获取，存入 PostgreSQL 后同步至 Neo4j。现在需要扩展图谱的**概念题材**维度，这是知识图谱演进路线的阶段一。

当前数据流向：`Tushare API → data_engineering (Provider + PostgreSQL) → knowledge_center (Adapter) → Neo4j`

约束条件：

- Tushare 积分不足（2000），概念接口不可用，改用 **akshare**（底层数据源为东方财富）
- akshare 概念相关接口为同步 API，需包装为异步调用
- 概念-股票映射为**多对多**关系（一股多概念），与现有行业等一对一维度关系不同
- akshare 返回的股票代码格式（如 `000001`）与系统标准格式（`000001.SZ`）不同，需要转换

## Goals / Non-Goals

**Goals:**

- 在 `data_engineering` 模块新增 akshare 概念数据提供者（Provider Port + Adapter），提供概念列表和成份股查询
- 概念数据持久化到 PostgreSQL（`concept` + `concept_stock` 表），与股票数据管理模式一致
- 在 Neo4j 图谱中新增 `Concept` 节点和 `BELONGS_TO_CONCEPT` 关系
- 支持两阶段同步：akshare → PostgreSQL（DE），PostgreSQL → Neo4j（KC）
- 现有邻居查询和关系网络查询自然扩展到概念维度

**Non-Goals:**

- 关联强度/权重（龙头 vs 跟风）
- 概念热度指数（heat_score）
- 概念层级树（SUB_CONCEPT_OF）
- 增量同步（MVP 仅支持全量刷新）
- 入选理由（reason 属性）

## Decisions

### D1: akshare 适配器归属 data_engineering 模块

**选择**: 在 `data_engineering/infrastructure/external_apis/akshare/` 下新建概念数据客户端。

**理由**:

- 与现有 Tushare 数据源的组织方式一致（`external_apis/tushare/`）
- `data_engineering` 的职责是"数据底座"，所有外部数据源的对接归该模块
- `knowledge_center` 通过 Adapter 消费，保持依赖方向不变（KC → DE，不反向）

**备选方案**: 直接在 `knowledge_center` 的 `infrastructure/` 中调用 akshare → 违反已建立的数据流模式，使两个模块都直接依赖外部 API，增加耦合。

### D2: 概念数据持久化到 PostgreSQL

**选择**: 概念数据从 akshare 获取后先持久化到 PostgreSQL（`concept` + `concept_stock` 表），`knowledge_center` 从 PostgreSQL 读取后同步到 Neo4j。数据流与现有股票数据完全一致：`akshare → DE(PostgreSQL) → KC(Neo4j)`。

**理由**:

- **架构一致性**：与现有 `Tushare → PostgreSQL → Neo4j` 的数据流模式完全一致，不引入第二套数据流
- **数据源可靠性隔离**：akshare 是社区库，底层爬取东方财富数据，稳定性不如商业 API。PostgreSQL 提供"最后已知好状态"兜底
- **演进基础**：后续概念热度计算需要关联市场行情数据（JOIN），历史变更追踪需要快照——这些都依赖 PostgreSQL 中有概念数据
- **消除直通脆弱性**：有本地数据后，Neo4j 同步不再依赖 akshare 可用性

**备选方案**: akshare → Neo4j 直通（不建 PostgreSQL 中间表）→ 开发更快，但破坏架构一致性，后续演进需补建并改数据流。

**数据模型**:

```
concept 表:
  id          SERIAL PRIMARY KEY
  code        VARCHAR(20) UNIQUE NOT NULL   -- 东方财富板块代码 (BK0493)
  name        VARCHAR(100) NOT NULL         -- 概念名称 (低空经济)
  created_at  TIMESTAMP DEFAULT NOW()
  updated_at  TIMESTAMP DEFAULT NOW()

concept_stock 表:
  id             SERIAL PRIMARY KEY
  concept_code   VARCHAR(20) NOT NULL        -- FK → concept.code
  third_code     VARCHAR(20) NOT NULL        -- 股票代码 (000001.SZ)
  stock_name     VARCHAR(100)                -- 股票名称（冗余字段，便于查询）
  created_at     TIMESTAMP DEFAULT NOW()
  UNIQUE(concept_code, third_code)
```

### D3: Concept 节点以 code 为唯一约束键

**选择**: 使用东方财富概念板块代码（如 `BK0493`）作为 `Concept.code` 唯一键。

**理由**:

- 代码比名称更稳定（名称可能修改，如"元宇宙"更名为"虚拟现实"）
- 东方财富的板块代码具有唯一性和持久性
- 与 Stock 节点使用 `third_code` 作为唯一键的设计风格一致

**备选方案**: 使用概念名称作为唯一键 → 名称变更会导致数据不一致和重复节点。

### D4: 两阶段同步与"先清后建"策略

**选择**: 采用两阶段同步模型，与现有股票同步模式一致：

- **阶段一（DE 内部）**：`SyncConceptDataCmd` 从 akshare 获取最新概念数据，全量替换 PostgreSQL 中的 `concept` + `concept_stock` 表（先清后建）
- **阶段二（KC 同步）**：`SyncConceptGraphCmd` 从 DE 的 PostgreSQL 读取概念数据，同步到 Neo4j（先删关系后重建）

两个阶段独立触发，与股票数据的"DE 先同步到 PG → KC 再同步到 Neo4j"模式一致。

**理由**:

- 概念-股票映射是多对多关系，成份股可能被移出概念，MERGE 无法处理移除
- PostgreSQL 作为 source of truth，Neo4j 的"先清后建"有数据兜底
- 概念数据量可控（~300 概念 × ~数千映射），全量重建性能可接受
- 后续可升级为 diff-based 策略（基于 PostgreSQL 中的新旧数据对比），无需改架构

**备选方案**:

- 单阶段直通（akshare → Neo4j）→ 已否决，见 D2
- Diff-based 增量 → 复杂度高，MVP 不需要，但 PostgreSQL 为未来启用此策略提供了基础

### D5: 股票代码格式转换由 akshare Adapter 负责

**选择**: `AkShareConceptClient` 内部将东方财富的股票代码（`000001`）转换为系统标准的 `third_code` 格式（`000001.SZ`）。

**理由**:

- 代码格式转换是数据适配层的职责，对上层透明
- 转换规则：`6` 开头 → `.SH`（上交所），`0/3` 开头 → `.SZ`（深交所），`4/8` 开头 → `.BJ`（北交所）
- 确保与 Neo4j 中已有 Stock 节点的 `third_code` 能正确关联（MATCH 而非 CREATE）

### D6: Provider Port 设计为两个独立方法

**选择**: `IConceptDataProvider` 提供 `fetch_concept_list()` 和 `fetch_concept_constituents(symbol)` 两个方法。

**理由**:

- 职责分离：概念列表获取 vs 成份股获取
- 调用方（sync command）可灵活控制并发策略和逐概念错误处理
- 便于单独测试和 mock

**备选方案**: 单一方法 `fetch_all_concepts_with_stocks()` → 灵活性低，难以实现逐概念的错误隔离与重试。

### D7: 概念同步 API 使用 target 参数区分同步类型

**选择**: 扩展现有 `POST /api/v1/knowledge-graph/sync` 端点，新增 `target` 参数（`stock` / `concept` / `all`），默认 `stock` 以保持向后兼容。

**理由**:

- 复用现有端点，避免 API 膨胀
- `target` 默认值为 `stock`，不影响现有调用行为
- 未来新增数据类型（如供应链）时，可继续扩展 `target` 枚举

**备选方案**: 新建独立端点 `POST /api/v1/knowledge-graph/sync-concepts` → 语义重复，维护成本高。

### D8: DE 概念同步通过独立命令触发

**选择**: DE 模块新增 `SyncConceptDataCmd`，负责从 akshare 获取概念数据并写入 PostgreSQL。该命令通过 DE 的 REST API 或调度器触发，与 KC 的图谱同步解耦。

**理由**:

- 与现有股票同步模式一致（`SyncStockListCmd` 独立于 KC 图谱同步）
- DE 和 KC 的同步各自独立，故障隔离：akshare 挂了不影响 KC 从 PG 同步到 Neo4j
- 同步频率可独立控制（DE 可以每天同步一次 akshare，KC 按需同步到 Neo4j）

**同步策略**: DE 概念同步采用全量替换——先清空 `concept_stock` 表，UPSERT `concept` 表，再批量插入新的 `concept_stock` 记录。简单可靠，概念数据量可控。

## Risks / Trade-offs

- **[API 限流]** 全量获取 ~300 个概念的成份股需 ~300 次 akshare API 调用。→ **缓解**: Adapter 中加入可配置的请求间隔（默认 0.3s），总耗时约 1.5-2 分钟，作为后台批量任务可接受。
- **[代码转换精度]** 股票代码格式转换可能遗漏特殊情况。→ **缓解**: 转换失败时记录 WARNING 日志并跳过，不中断同步；后续可补充规则。
- **[Neo4j 先清后建的短暂不一致]** KC 同步期间概念关系处于"已删除但未重建"状态。→ **缓解**: PostgreSQL 作为 source of truth 不受影响；Neo4j 重建在可控时间窗口内完成。
- **[akshare 接口变更]** akshare 是社区维护的开源库，接口可能变更。→ **缓解**: 通过 Provider Port 抽象隔离；变更时只需修改 Adapter 实现，不影响上层逻辑。PostgreSQL 中保有最后成功获取的数据作为兜底。
- **[两阶段同步的操作复杂度]** 用户需先触发 DE 同步再触发 KC 同步。→ **缓解**: KC 的 `target=all` 模式可串联两个阶段；后续可加调度器自动编排。
