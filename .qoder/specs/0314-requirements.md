# 0314 需求实施规范

## Context

当前项目 good-life-assistant 存在以下问题需要解决：
1. **持仓总览页面信息冗余** -- 每只股票下方展示的 MA 信号、RSI、5日涨跌、期权情绪卡片过于庞杂，需要精简；成本价字段不正确（当前是摊薄成本价，需改为平均成本价）；最后一列"今日盈亏%"重复信息，应改为"未实现盈亏"
2. **对话框缺乏实时反馈** -- 发送消息后只显示 3 个跳动灰点，用户无法知道 Agent 正在执行什么操作
3. **LLM 配置单一** -- 整个项目只能用一个 LLM（ChatOpenAI），无法支持 Claude/Gemini/Qwen 等多模型，也没有模型管理界面
4. **数据持久化原始** -- 模块配置用 JSON 文件保存，不利于扩展和查询

## 实施分为 4 个阶段，按依赖顺序执行

---

## Phase 1: SQLite + SQLAlchemy 数据库层 (需求4)

> 其他功能的基础，先完成。

### 1.1 新建数据库基础设施

**新建** `server/db/__init__.py`

**新建** `server/db/session.py`
- 创建 SQLAlchemy engine（`sqlite:///data/app.db`）
- 定义 `Base = declarative_base()`
- 创建 `SessionLocal` 工厂
- `init_db()` 函数：调用 `Base.metadata.create_all(engine)` 建表

**新建** `server/db/models.py` -- ORM 模型
```python
class LLMModel(Base):
    __tablename__ = "llm_models"
    id: int  # PK autoincrement
    name: str  # UNIQUE, 用户自定义名称, e.g. "DeepSeek-主力"
    provider: str  # enum: deepseek/openai/anthropic/google/qwen
    model: str  # 模型名, e.g. "deepseek-chat", "claude-3-5-sonnet"
    api_key: str  # 加密存储
    base_url: str | None  # 自定义 endpoint
    is_default: bool  # 全局默认标记
    extra_params: str | None  # JSON string, 额外参数
    created_at, updated_at: datetime

class ModelAssignment(Base):
    __tablename__ = "model_assignments"
    id: int  # PK
    scope: str  # UNIQUE, e.g. "global", "agent.router", "module.stock"
    model_id: int  # FK -> llm_models.id
    temperature: float | None
    created_at, updated_at: datetime

class ModuleConfig(Base):
    __tablename__ = "module_configs"
    module_id: str  # PK, e.g. "stock"
    enabled: bool
    config_json: str  # JSON string
    updated_at: datetime
```

**新建** `server/db/crypto.py`
- 使用 `cryptography.fernet.Fernet` 进行 API Key 加密/解密
- 密钥从 `ENCRYPTION_KEY` 环境变量读取，未设置则自动生成并写入 `.env`

**新建** `server/db/repositories.py`
- `LLMModelRepository`: CRUD for llm_models
- `ModelAssignmentRepository`: CRUD for model_assignments
- `ModuleConfigRepository`: CRUD for module_configs（替代 JSON 文件读写）

**新建** `server/db/service.py`
- `LLMService`:
  - `resolve_model_for_scope(scope: str) -> ResolvedLLMConfig`: 按优先级解析模型
    - 解析链: 精确 scope -> 上级 scope -> "global" -> .env 回退
    - 例: `"module.stock.recommendations"` -> `"module.stock"` -> `"global"` -> Settings
  - `get_all_models()`, `create_model()`, `update_model()`, `delete_model()`
  - `get_assignments()`, `set_assignment()`, `delete_assignment()`
- `ModuleConfigService`: 封装模块配置的增删改查

### 1.2 迁移现有 JSON 配置到 SQLite

**新建** `server/db/migration.py`
- 读取 `data/modules_config.json`
- 将模块配置插入 `module_configs` 表
- 将 `.env` 中的 LLM 配置作为默认模型插入 `llm_models` 表
- 启动时自动检测：如果 `llm_models` 表为空则执行迁移

### 1.3 修改现有文件

**修改** `server/config.py`
- 新增 `db_path: str = "data/app.db"` 和 `encryption_key: str = ""`

**修改** `server/main.py`
- 在 lifespan 中调用 `init_db()` 和迁移检查

**修改** `server/modules/registry.py`
- `_load_config()` / `_save_config()` / `get_module_config()` / `update_module_config()` 改为调用 `ModuleConfigService`
- 保持 ModuleRegistry 对外接口不变

### 关键文件清单
| 操作 | 文件路径 |
|------|---------|
| 新建 | `server/db/__init__.py` |
| 新建 | `server/db/session.py` |
| 新建 | `server/db/models.py` |
| 新建 | `server/db/crypto.py` |
| 新建 | `server/db/repositories.py` |
| 新建 | `server/db/service.py` |
| 新建 | `server/db/migration.py` |
| 修改 | `server/config.py` |
| 修改 | `server/main.py` |
| 修改 | `server/modules/registry.py` |

---

## Phase 2: 多模型 LLM 管理 (需求3)

> 依赖 Phase 1 的数据库层。

### 2.1 重构 LLM 工厂

**修改** `server/core/llm.py`
- 引入 `LLMService.resolve_model_for_scope()`
- 新增 `create_llm_for_scope(scope: str, **overrides) -> BaseChatModel`
  - 调用 service 获取 ResolvedLLMConfig
  - 根据 provider 创建对应实例：
    - `deepseek` / `openai` / `qwen` -> `ChatOpenAI`（OpenAI 兼容）
    - `anthropic` -> `ChatAnthropic`（需 `langchain-anthropic`）
    - `google` -> `ChatGoogleGenerativeAI`（需 `langchain-google-genai`）
  - 使用 lazy import 避免未安装的依赖报错
- 保留 `create_llm()` 作为兼容入口，内部调用 `create_llm_for_scope("global")`

### 2.2 所有 LLM 调用点添加 scope 参数

| 调用位置 | scope 值 |
|---------|----------|
| `server/agent/router.py` router_node | `"agent.router"` |
| `server/agent/graph.py` chat_agent_node | `"agent.chat"` |
| `server/agent/nodes/stock_agent.py` stock_agent_node | `"module.stock.agent"` |
| `server/modules/stock/llm_summary.py` generate_options_wall_summary | `"module.stock.options_wall"` |
| `server/modules/stock/llm_summary.py` generate_portfolio_recommendations | `"module.stock.recommendations"` |

每处将 `create_llm(temperature=X)` 改为 `create_llm_for_scope("scope", temperature=X)`。

### 2.3 后端 API

**修改** `server/api/admin.py` -- 新增以下 endpoints:
```
GET    /admin/llm/models          # 列出所有模型
POST   /admin/llm/models          # 新增模型
PUT    /admin/llm/models/{id}     # 修改模型
DELETE /admin/llm/models/{id}     # 删除模型
GET    /admin/llm/assignments     # 列出所有 scope 分配
PUT    /admin/llm/assignments     # 设置 scope 分配 (body: {scope, model_id, temperature})
DELETE /admin/llm/assignments/{scope}  # 删除某 scope 分配
GET    /admin/llm/scopes          # 列出所有可配置的 scope
```

### 2.4 前端模型管理页面

**新建** `web/src/pages/admin/ModelManagementPage.tsx`
- 模型列表：表格展示所有已添加模型，支持编辑/删除
- 新增模型表单：provider 下拉选择 -> 自动填充 base_url -> 输入 model/api_key/name
- scope 分配面板：以表格形式展示所有 scope，每个 scope 可选择模型 + 设置 temperature
- provider 预设模板：
  - DeepSeek: base_url=`https://api.deepseek.com`, models: deepseek-chat, deepseek-reasoner
  - OpenAI: base_url 留空, models: gpt-4o, gpt-4o-mini
  - Anthropic: base_url 留空, models: claude-3-5-sonnet, claude-3-haiku
  - Google: base_url 留空, models: gemini-2.0-flash, gemini-2.5-pro
  - Qwen: base_url=`https://dashscope.aliyuncs.com/compatible-mode/v1`, models: qwen-plus, qwen-turbo

**修改** `web/src/App.tsx`
- 新增路由: `/admin/models` -> `ModelManagementPage`

**修改** `web/src/pages/admin/AdminPage.tsx`
- LLM 配置区域改为链接到 `/admin/models` 的入口卡片
- 移除原有的只读 LLM 配置展示

### 关键文件清单
| 操作 | 文件路径 |
|------|---------|
| 修改 | `server/core/llm.py` |
| 修改 | `server/agent/router.py` |
| 修改 | `server/agent/graph.py` |
| 修改 | `server/agent/nodes/stock_agent.py` |
| 修改 | `server/modules/stock/llm_summary.py` |
| 修改 | `server/api/admin.py` |
| 新建 | `web/src/pages/admin/ModelManagementPage.tsx` |
| 修改 | `web/src/App.tsx` |
| 修改 | `web/src/pages/admin/AdminPage.tsx` |

---

## Phase 3: 持仓总览页面优化 (需求1)

> 独立于 Phase 1/2，但放在后面以确保数据库层稳定。

### 3.1 移除每只股票的分析卡片

**修改** `web/src/modules/stock/PortfolioView.tsx`
- 删除 `SignalBadge` 组件 (L343-359)
- 删除 `RSIGauge` 组件 (L361-371)
- 删除 `AnalysisSection` 中的 holdings.map 循环 (L416-475)，只保留 `<RecommendationsBlock />` 和底部风险提示

### 3.2 修改成本价字段

> Futu API `position_list_query` 字段参考 (https://openapi.futunn.com/futu-api-doc/trade/get-position-list.html):
> - `average_cost`: 平均成本价（模拟证券账户不适用，OpenD >= 9.2.5208）
> - `diluted_cost`: 摊薄成本价（即原 cost_price，OpenD >= 9.2.5208）
> - `unrealized_pl`: 未实现盈亏（模拟证券账户不适用）

**修改** `server/modules/stock/account.py` `get_positions()`
- 在 positions.append 中新增字段:
  - `"avg_cost_price": safe_float(row.get("average_cost"))` -- 平均成本价
  - `"unrealized_pl": safe_float(row.get("unrealized_pl"))` -- 单只股票未实现盈亏
- 保留原有 `cost_price` 字段不删除（其他地方可能使用）

**修改** `web/src/stores/stockStore.ts`
- `Position` interface 新增 `avg_cost_price?: number` 和 `unrealized_pl?: number`

**修改** `web/src/modules/stock/PortfolioView.tsx` `PositionTable`
- 表头 "成本价" -> "平均成本价"
- 数据列从 `pos.cost_price` -> `pos.avg_cost_price ?? pos.cost_price`（模拟账户下 average_cost 为空时 fallback）

### 3.3 替换最后一列

**修改** `web/src/modules/stock/PortfolioView.tsx` `PositionTable`
- 最后一列表头从 "今日盈亏%" 改为 "未实现盈亏"
- 数据从 `chgPct` 改为 `pos.unrealized_pl ?? pos.pl_val`（模拟账户下 unrealized_pl 为空时 fallback 到 pl_val）
- 颜色: 值 `>= 0` 绿色, `< 0` 红色
- 格式: `{val >= 0 ? '+' : ''}${fmt(val)}`

### 关键文件清单
| 操作 | 文件路径 |
|------|---------|
| 修改 | `web/src/modules/stock/PortfolioView.tsx` |
| 修改 | `web/src/stores/stockStore.ts` |
| 修改 | `server/modules/stock/account.py` |

---

## Phase 4: 对话框实时进度展示 (需求2)

> 依赖后端 SSE 事件管道的改造。

### 4.1 后端进度事件系统

**新建** `server/agent/progress.py`
```python
import contextvars
import queue

progress_queue: contextvars.ContextVar[queue.Queue | None] = contextvars.ContextVar(
    "progress_queue", default=None
)

def emit_progress(step: str, detail: str = ""):
    q = progress_queue.get(None)
    if q is not None:
        q.put_nowait({"step": step, "detail": detail})
```

### 4.2 在各节点中发送进度事件

**修改** `server/agent/router.py`
- 在意图分类前: `emit_progress("analyzing_intent", "正在分析意图...")`
- 分类完成后: `emit_progress("routed", f"路由到{intent}模块")`

**修改** `server/agent/nodes/stock_agent.py`
- 进入节点时: `emit_progress("stock_agent_start", "正在启动股票分析...")`
- 每次工具调用前: `emit_progress("tool_call", f"正在调用 {tool_name}...")`
- 工具调用完成: `emit_progress("tool_result", f"{tool_name} 已完成")`
- 生成最终回复前: `emit_progress("generating", "正在生成分析报告...")`

**修改** `server/agent/graph.py`
- `chat_agent_node` 中: `emit_progress("chat_thinking", "正在思考回复...")`

### 4.3 改造 SSE 端点

**修改** `server/api/chat.py`
- 创建 `queue.Queue` 实例
- 使用 `contextvars.copy_context()` 将 queue 传入线程
- 不再等 `graph.invoke()` 完成后才发事件，改用 `asyncio.to_thread` + 并发 queue 消费：

```python
async def event_generator():
    q = queue.Queue()
    ctx = contextvars.copy_context()
    ctx.run(progress_queue.set, q)

    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, lambda: ctx.run(graph.invoke, input_state))

    # 边消费进度边等结果
    while not future.done():
        try:
            event = await asyncio.to_thread(q.get, timeout=0.1)
            yield _format_sse("progress", event)
        except queue.Empty:
            continue

    result = future.result()
    # ... send ui_commands + message + done
```

### 4.4 前端进度展示

**修改** `web/src/api/client.ts` `fetchSSE`
- handlers 中新增 `onProgress?: (data: { step: string; detail: string }) => void`
- switch 中新增 `case 'progress': handlers.onProgress?.(data)`

**修改** `web/src/stores/chatStore.ts`
- `ChatMessage` interface 新增 `progressMessage?: string`
- `ChatState` 新增 `progressMessage: string`
- 在 `sendMessage` 的 fetchSSE handlers 中新增:
  ```
  onProgress: (data) => {
    set({ progressMessage: data.detail });
  }
  ```
- `onDone` 中清除: `set({ isStreaming: false, progressMessage: '' })`

**修改** `web/src/components/chat/MessageBubble.tsx`
- Props 新增 `progressMessage?: string`
- 当 `isStreaming && !message.content` 时，若有 progressMessage 则显示文字而非跳动灰点:
  ```tsx
  {progressMessage ? (
    <div className="flex items-center gap-2 text-gray-500 text-xs">
      <Loader2 className="w-3.5 h-3.5 animate-spin" />
      <span>{progressMessage}</span>
    </div>
  ) : (
    <div>/* 原有 bouncing dots */</div>
  )}
  ```

**修改** `web/src/components/chat/MessageList.tsx`
- 将 `progressMessage` 从 chatStore 传递给最后一条 assistant MessageBubble

### 关键文件清单
| 操作 | 文件路径 |
|------|---------|
| 新建 | `server/agent/progress.py` |
| 修改 | `server/agent/router.py` |
| 修改 | `server/agent/nodes/stock_agent.py` |
| 修改 | `server/agent/graph.py` |
| 修改 | `server/api/chat.py` |
| 修改 | `web/src/api/client.ts` |
| 修改 | `web/src/stores/chatStore.ts` |
| 修改 | `web/src/components/chat/MessageBubble.tsx` |
| 修改 | `web/src/components/chat/MessageList.tsx` |

---

## 依赖安装

```bash
# 后端新增
pip install sqlalchemy cryptography langchain-anthropic langchain-google-genai

# 前端无新增依赖
```

---

## 待确认事项

无 -- 所有待确认事项已解决。

---

## 验证方案

### Phase 1 验证
- 启动服务后检查 `data/app.db` 是否自动创建
- 若存在 `data/modules_config.json`，验证其数据已迁移至 SQLite
- 通过 `/api/admin/modules` 确认模块配置正常读取

### Phase 2 验证
- 通过 `/api/admin/llm/models` API 创建多个模型
- 通过 `/api/admin/llm/assignments` 配置 scope 分配
- 发送 chat 消息，观察日志确认使用了正确 scope 对应的模型
- 浏览器打开 `/admin/models` 页面，验证模型管理 CRUD 和 scope 分配 UI

### Phase 3 验证
- 浏览器打开持仓总览页面
- 确认每只股票下方的分析卡片（MA信号/RSI/5日涨跌/期权情绪）已移除
- 确认表头显示"平均成本价"（字段确认后）
- 确认最后一列显示"未实现盈亏"金额，绿正红负

### Phase 4 验证
- 浏览器打开对话框，发送一条股票相关的消息
- 确认对话气泡中显示实时进度文字（"正在分析意图..." -> "路由到stock模块" -> "正在调用 xxx..." -> 最终回复）
- 确认进度文字在最终回复到达后消失

### 全局验证
- TypeScript 编译检查: `npx tsc --noEmit`
- 后端无报错启动: `python -m server.main`
