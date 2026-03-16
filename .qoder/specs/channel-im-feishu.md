# Channel 通道系统 + 飞书 IM 接入

## Context

现有系统仅支持 Web SSE 聊天通道。需要增加 Channel（通道）概念，支持多种交互方式。第一个 IM 通道实现为飞书机器人，通过 WebSocket 长连接接收消息（无需域名/公网端口），调用同一套 Agent 图返回结果。

**核心问题**：工具（如 `get_portfolio`）需要根据通道来源区别处理 —— Web 通道返回 `_ui_command` 触发前端页面渲染，IM 通道则应直接获取数据返回文字摘要，因为 IM 没有 UI 功能区。

**核心决策**：
1. Channel 与 Module 完全分离 —— Channel 是消息接入层，Module 是功能扩展层
2. 通过 `contextvars` 传播通道类型到工具层，工具内部根据通道做分支处理

## 架构

```
FastAPI (main thread)
  ├── asyncio event loop
  │     ├── Web Channel (SSE /api/chat/stream, channel_context="web")
  │     └── Admin API (/api/admin/channels/*)
  ├── daemon Thread: FeishuChannel
  │     └── lark.ws.Client.start() (阻塞, 自带 auto_reconnect)
  │           └── on_message → _invoke_agent(text, channel="im") → reply(post)
  └── (未来) daemon Thread: 其他 IM ...
```

### 通道感知数据流

```
Web 通道:
  chat.py 设置 channel_context="web"
    → graph.invoke → stock_agent → get_portfolio()
    → 检测 channel="web" → 返回 _ui_command + 空数据 → 前端加载页面

IM 通道:
  FeishuChannel 设置 channel_context="im"
    → graph.invoke → stock_agent → get_portfolio()
    → 检测 channel="im" → 调用 service 获取实际数据 → 返回文字摘要给 LLM
    → LLM 总结 → 飞书回复
```

---

## Phase 1: 通道上下文 + 数据库 + 基类

### 1.1 通道上下文传播机制
**修改**: `server/agent/progress.py`

新增 `channel_context` ContextVar，与 `progress_queue` 同级：

```python
channel_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "channel_context", default="web"
)

def get_channel() -> str:
    """获取当前通道类型，默认 'web'"""
    return channel_context.get("web")
```

**修改**: `server/api/chat.py`

在 `ctx.run()` 设置 progress_queue 的同一位置，增加设置 channel_context：
```python
ctx.run(progress_queue.set, q)
ctx.run(channel_context.set, "web")  # Web 通道标识
```

### 1.2 工具层通道感知改造
**修改**: `server/modules/stock/tools.py`

每个工具内部根据 `get_channel()` 做分支：

**`get_portfolio()`**:
```python
@tool
def get_portfolio() -> dict:
    from server.agent.progress import get_channel
    if get_channel() == "im":
        # IM：直接获取持仓数据返回给 LLM 做文字总结
        data = service.get_portfolio_summary()  # 调用已有 service
        return data  # 无 _ui_command，LLM 会基于数据生成文字摘要
    # Web：触发前端面板，数据由前端独立加载
    return {
        "message": "已触发持仓面板，前端正在加载数据",
        "_ui_command": {"module": "stock", "action": "show_portfolio", "data": {}},
    }
```

**`get_stock_trend()`、`get_options_chain()`、`get_portfolio_analysis()`**:
```python
# 这些工具始终获取真实数据（web 和 im 都需要）
# 区别仅在于：web 额外附加 _ui_command，im 不附加
data = service.get_stock_trend_data(ticker, period=period)
if get_channel() == "web":
    data["_ui_command"] = {"module": "stock", "action": "show_trend", "data": data}
return data
```

### 1.3 Agent 节点通道感知
**修改**: `server/agent/nodes/stock_agent.py`

在构建 system_prompt 后，根据通道追加提示：
```python
system_prompt = module.get_system_prompt()
if get_channel() == "im":
    system_prompt += "\n\n【重要】当前是 IM 通道，无法展示图表和页面。请用文字详细描述所有数据和分析结果，确保用户不看图表也能完整理解。"
```

**修改**: `server/agent/graph.py` 的 `chat_agent_node`

同样追加 IM 通道提示到 chat 消息中（可选，chat 节点通常不涉及 UI）。

### 1.4 新增 ChannelConfig ORM 模型
**修改**: `server/db/models.py`

```python
class ChannelConfig(Base):
    __tablename__ = "channel_configs"
    channel_id    = Column(String(100), primary_key=True)   # "feishu"
    channel_type  = Column(String(50), nullable=False)       # "im"
    enabled       = Column(Boolean, default=False)
    config_json   = Column(Text, default="{}")               # 敏感字段加密存储
    status        = Column(String(50), default="stopped")    # stopped/running/error
    status_message = Column(Text, nullable=True)
    updated_at    = Column(DateTime, default=_utcnow, onupdate=_utcnow)
```

确保 `init_db()` import 新模型触发建表。

### 1.5 ChannelConfigRepository
**修改**: `server/db/repositories.py`

新增 `ChannelConfigRepository` 类：
- `get(channel_id)`, `get_all()`, `upsert(channel_id, channel_type, enabled, config)` 
- `update_enabled()`, `update_config()`, `update_status(channel_id, status, message)`
- `to_dict(obj, mask_secrets=True)` — 对 config 中 `app_secret` 等敏感字段掩码
- 敏感字段写入时使用 `encrypt_api_key()`，读出时 `decrypt_api_key()`

### 1.6 ChannelConfigService
**修改**: `server/db/service.py`

新增 `ChannelConfigService` + `get_channel_config_service()` 单例，与 ModuleConfigService 结构对称。

### 1.7 通道基类
**新建**: `server/channels/__init__.py`（空）
**新建**: `server/channels/base.py`

```python
class BaseChannel(ABC):
    channel_id: str
    channel_type: str        # "im" / "web"
    display_name: str
    description: str
    default_config: dict = {}
    config_schema: list[dict] = []  # 表单元数据，前端动态渲染

    @abstractmethod
    def start(self, config: dict) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...
    @abstractmethod
    def test_connection(self, config: dict) -> dict: ...  # {"success": bool, "message": str}
    @property
    @abstractmethod
    def is_running(self) -> bool: ...

class BaseIMChannel(BaseChannel):
    channel_type = "im"

    def _invoke_agent(self, user_message: str) -> str:
        """调用 Agent 图获取回复（同步，设置 channel_context="im"）"""
        from server.agent.graph import get_graph
        from server.agent.progress import channel_context
        from langchain_core.messages import HumanMessage, AIMessage

        graph = get_graph()
        input_state = {
            "messages": [HumanMessage(content=user_message)],
            "current_module": None,
            "ui_commands": [],
            "intent": None,
        }
        # 关键：设置通道上下文为 "im"，工具据此做分支处理
        ctx = contextvars.copy_context()
        ctx.run(channel_context.set, "im")
        result = ctx.run(graph.invoke, input_state)

        # 提取最终文本（忽略 ui_commands）
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        return "抱歉，我暂时无法回答。"
```

---

## Phase 2: ChannelRegistry + 飞书实现

### 2.1 ChannelRegistry
**新建**: `server/channels/registry.py`

```python
class ChannelRegistry:
    channels: dict[str, BaseChannel]
    _threads: dict[str, threading.Thread]

    def register(channel)                  # 注册实例，DB 无记录则自动 upsert default
    def discover_channels()                # 导入并注册 FeishuChannel
    def start_channel(channel_id)          # 读 DB 配置 → channel.start(config) in daemon thread
    def stop_channel(channel_id)           # channel.stop() → 更新 DB status
    def start_enabled_channels()           # 启动所有 enabled=True 的通道
    def stop_all_channels()                # 关闭所有运行中通道
    def get_all_channel_info() -> list     # 元数据 + 运行状态
```

单例: `get_channel_registry()`

### 2.2 飞书通道
**新建**: `server/channels/feishu/__init__.py`（空）
**新建**: `server/channels/feishu/channel.py`

```python
class FeishuChannel(BaseIMChannel):
    channel_id = "feishu"
    display_name = "飞书机器人"
    description = "通过飞书机器人接收和回复消息"
    default_config = {"app_id": "", "app_secret": ""}
    config_schema = [
        {"key": "app_id", "label": "App ID", "type": "text", "required": True, "secret": False},
        {"key": "app_secret", "label": "App Secret", "type": "password", "required": True, "secret": True},
    ]
```

**核心方法**:
- `start(config)`: 构建 `EventDispatcherHandler` + `lark.ws.Client`，调用 `ws_client.start()`（阻塞，Registry 在 daemon thread 中执行）
- `stop()`: 设置 `_running=False`
- `_on_message(data)`: 解析 `data.event.message.content` → `_invoke_agent(text)` → 转为 post 格式 → `client.im.v1.message.reply()`
- `_text_to_post(text)`: Markdown → 飞书 post JSON（按段落拆分，识别 `**粗体**`、`[链接](url)` 等标记）
- `test_connection(config)`: 用 `app_id/app_secret` 构建临时 Client，调用获取 tenant_access_token 验证凭证

### 2.3 依赖
**修改**: `pyproject.toml`

新增 `lark-oapi>=1.4.0`

---

## Phase 3: API + 生命周期

### 3.1 Admin API
**新建**: `server/api/channels.py`

| 端点 | 方法 | 功能 |
|------|------|------|
| `/channels` | GET | 列出所有通道 + 状态 |
| `/channels/{id}/config` | GET | 获取配置（secret 掩码） |
| `/channels/{id}/config` | PUT | 更新配置 |
| `/channels/{id}/toggle` | PUT | 启用/禁用（触发 start/stop） |
| `/channels/{id}/test` | POST | 测试连接 |

`toggle` 关键逻辑：enabled=True 时先存 DB 再 start_channel，enabled=False 时先 stop_channel 再存 DB。

### 3.2 Lifespan 集成
**修改**: `server/main.py`

启动：`channel_registry.discover_channels()` → `channel_registry.start_enabled_channels()`
关闭：`channel_registry.stop_all_channels()`

路由挂载：`app.include_router(channel_router, prefix="/api/admin")`

---

## Phase 4: 前端

### 4.1 AdminLayout 导航
**修改**: `web/src/pages/admin/AdminLayout.tsx`

NAV_ITEMS 新增（在"模块配置"之后）:
```
{ divider: true, label: '通道管理' }
{ path: '/admin/channels', label: '通道管理', icon: Radio }
```

### 4.2 ChannelsPage
**新建**: `web/src/pages/admin/ChannelsPage.tsx`

通道列表卡片：
- 名称 + 类型标签 (`im`)
- 状态徽标：🟢 running / 🔴 stopped / 🟡 error
- 启用/禁用开关
- "配置" 链接 → `/admin/channels/{channelId}`
- "测试" 按钮 → POST test → 显示结果

### 4.3 ChannelConfigPage（通用动态表单）
**新建**: `web/src/pages/admin/ChannelConfigPage.tsx`

根据后端返回的 `config_schema` 动态渲染表单：
- `type: "text"` → 文本输入框
- `type: "password"` → 密码输入框 + "已配置" 提示
- 保存按钮 + 测试按钮
- 顶部显示连接状态

### 4.4 路由
**修改**: `web/src/App.tsx`

```
/admin/channels            → <AdminLayout><ChannelsPage /></AdminLayout>
/admin/channels/:channelId → <AdminLayout><ChannelConfigPage /></AdminLayout>
```

### 4.5 API Client
**修改**: `web/src/api/client.ts`

提升 `postJSON` 为公共函数（当前仅在 ModelManagementPage 本地定义）。

---

## 关键文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `server/channels/__init__.py` | 空 |
| 新建 | `server/channels/base.py` | BaseChannel + BaseIMChannel（含 _invoke_agent） |
| 新建 | `server/channels/registry.py` | ChannelRegistry 生命周期管理 |
| 新建 | `server/channels/feishu/__init__.py` | 空 |
| 新建 | `server/channels/feishu/channel.py` | 飞书 WebSocket 长连接实现 |
| 新建 | `server/api/channels.py` | Admin API |
| 新建 | `web/src/pages/admin/ChannelsPage.tsx` | 通道列表页 |
| 新建 | `web/src/pages/admin/ChannelConfigPage.tsx` | 通道配置页（动态表单） |
| 修改 | `server/agent/progress.py` | **新增 channel_context ContextVar + get_channel()** |
| 修改 | `server/api/chat.py` | **设置 channel_context="web"** |
| 修改 | `server/modules/stock/tools.py` | **工具根据 get_channel() 做 web/im 分支** |
| 修改 | `server/agent/nodes/stock_agent.py` | **IM 通道追加 system prompt 说明** |
| 修改 | `server/db/models.py` | 新增 ChannelConfig |
| 修改 | `server/db/repositories.py` | 新增 ChannelConfigRepository |
| 修改 | `server/db/service.py` | 新增 ChannelConfigService |
| 修改 | `server/main.py` | lifespan + 路由挂载 |
| 修改 | `pyproject.toml` | 新增 lark-oapi |
| 修改 | `web/src/App.tsx` | 新增路由 |
| 修改 | `web/src/pages/admin/AdminLayout.tsx` | 新增导航 |
| 修改 | `web/src/api/client.ts` | 提升 postJSON |

---

## 验证步骤

1. **DB**: 启动后 `data/app.db` 自动创建 `channel_configs` 表
2. **Web 通道不受影响**: 在 Web 聊天中发送"查看持仓" → 仍然触发 `_ui_command` 加载持仓页面
3. **API**: `GET /api/admin/channels` 返回 feishu 通道（默认 disabled）
4. **配置**: 前端 admin 配置页面填入 app_id/app_secret → 保存
5. **测试**: 点击"测试连接"→ 验证凭证有效性
6. **启用**: 开启飞书通道 → 后端日志显示 WebSocket 连接建立
7. **IM 消息（持仓）**: 飞书给机器人发"查看持仓" → 收到文字版持仓摘要（非空 UI 命令），包含实际持仓数据
8. **IM 消息（分析）**: 飞书发"分析一下" → 收到详细文字分析报告（无图表触发）
9. **重启**: 重启服务 → 飞书通道自动恢复连接
10. **TypeScript**: `npx tsc --noEmit` 无新增错误
