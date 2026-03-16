# Good Life Assistant - 项目初始化实施方案

## Context

用户需要创建一个"生活助手 Agent"全栈项目。项目采用左侧聊天框 + 右侧功能区的布局，通过对话驱动 Agent 加载不同功能模块页面。第一个模块是"富途股票持仓分析"，需从 `/Users/songxu/Documents/code/futu-trade/trade/` 迁移核心代码。

## 技术栈

- **后端**: Python (uv) + FastAPI + LangGraph + LangChain + DeepSeek
- **前端**: Vite + React + TypeScript + TailwindCSS + Recharts + Zustand
- **数据源**: yfinance + FutuOpenD 双通道
- **通信**: SSE 流式 + REST API

## 架构总览

```
浏览器 (React SPA)
 ├── ChatPanel (左侧) ── POST /api/chat/stream (SSE) ──┐
 └── ModulePanel (右侧) ── GET /api/modules/stock/*  ──┤
                                                        ▼
FastAPI 后端 (:8000)
 ├── API Router (chat SSE, admin REST, module REST)
 ├── LangGraph Agent (router → sub-agents)
 ├── Module System (registry + pluggable modules)
 └── Data Services (FutuOpenD + yfinance)
```

## 项目目录结构

```
good-life-assistant/
├── .env / .env.example
├── pyproject.toml
├── start.sh                      # 一键启动
├── server/
│   ├── main.py                   # FastAPI 入口
│   ├── config.py                 # pydantic-settings 配置
│   ├── core/
│   │   ├── llm.py                # LLM 工厂 (DeepSeek via ChatOpenAI)
│   │   └── schemas.py            # ChatMessage, UICommand, SSEEvent
│   ├── api/
│   │   ├── chat.py               # POST /api/chat/stream (SSE)
│   │   ├── admin.py              # 模块管理 API
│   │   └── modules/stock.py      # 股票数据 REST API
│   ├── agent/
│   │   ├── state.py              # AgentState TypedDict
│   │   ├── graph.py              # LangGraph 图定义
│   │   ├── router.py             # 意图分类路由节点
│   │   └── nodes/stock_agent.py  # 股票子 agent
│   └── modules/
│       ├── base.py               # BaseModule 抽象类
│       ├── registry.py           # ModuleRegistry 单例
│       └── stock/                # 富途股票模块
│           ├── module.py         # StockModule 声明
│           ├── tools.py          # 4个 LangChain tools
│           ├── service.py        # 业务编排层
│           ├── account.py        # ← futu-trade 迁移
│           ├── quote.py          # ← futu-trade 迁移
│           ├── connection.py     # ← futu-trade 迁移
│           ├── enums.py          # ← futu-trade 迁移
│           ├── utils.py          # ← futu-trade 迁移
│           ├── analysis.py       # ← analyze.py 迁移
│           └── config.py         # 模块级配置
├── web/
│   ├── package.json / vite.config.ts / tailwind.config.js
│   └── src/
│       ├── App.tsx               # Router: / → AppLayout, /admin → AdminPage
│       ├── api/                  # fetch + SSE 客户端
│       ├── stores/               # Zustand: chatStore, moduleStore, stockStore
│       ├── components/
│       │   ├── layout/           # AppLayout, ChatPanel, ModulePanel
│       │   └── chat/             # MessageList, MessageBubble, ChatInput
│       ├── modules/stock/        # PortfolioView, StockChart, OptionsChainView, AnalysisView
│       └── pages/admin/          # AdminPage, ModuleManager, ModuleConfigForm
└── data/
    └── modules_config.json       # 模块运行时配置
```

## SSE 通信协议

聊天通过 `POST /api/chat/stream` 返回 SSE 流，事件类型：

| 事件类型 | 数据格式 | 用途 |
|---------|---------|------|
| `message` | `{content: str}` | Agent 文字输出 (逐 token) |
| `ui_command` | `{module: str, action: str, data: dict}` | 驱动前端渲染模块页面 |
| `tool_call` | `{tool: str, args: dict}` | 工具调用通知 (显示 loading) |
| `error` | `{message: str}` | 错误信息 |
| `done` | `{}` | 流结束 |

## LangGraph Agent 图

```
START → router (意图分类)
         ├── "stock" → stock_agent (ReAct + tools) → END
         ├── "general" → chat_agent (纯 LLM) → END
         └── (未来模块...)
```

- **router**: 用 LLM (temperature=0) 分类用户意图到已启用的模块 ID
- **stock_agent**: `create_react_agent()` 绑定 4 个 tools，自主决定调用
- **chat_agent**: 通用对话，直接调 LLM

## 股票模块 Tools

| Tool | 功能 | 数据源 |
|------|------|--------|
| `get_portfolio` | 查询持仓+资金 | FutuOpenD + yfinance |
| `get_stock_trend` | 股票走势 (MA/RSI) | yfinance |
| `get_options_chain` | 期权链数据 | yfinance |
| `get_portfolio_analysis` | 完整分析报告 | FutuOpenD + yfinance |

每个 tool 返回结果时同时生成 `ui_command`，通过 SSE 下发给前端渲染。

## 数据流示例

用户输入"帮我看看我的持仓" →
1. POST /api/chat/stream
2. router 识别意图 → "stock"
3. stock_agent 调用 `get_portfolio` tool
4. SSE: `tool_call` → 前端显示 loading
5. SSE: `ui_command {action: "show_portfolio", data: {...}}` → 右侧渲染持仓页面
6. SSE: `message` → 左侧聊天显示 Agent 总结
7. SSE: `done` → 结束

## 从 futu-trade 迁移的文件

| 源文件 | 目标文件 | 说明 |
|--------|----------|------|
| `trade/account.py` | `server/modules/stock/account.py` | 改导入路径 |
| `trade/quote.py` | `server/modules/stock/quote.py` | 改导入路径 |
| `trade/connection.py` | `server/modules/stock/connection.py` | 改导入路径 |
| `trade/config.py` | `server/modules/stock/config.py` | 从 ModuleRegistry 读配置 |
| `trade/enums.py` | `server/modules/stock/enums.py` | 原样 |
| `trade/utils.py` | `server/modules/stock/utils.py` | 原样 |
| `analyze.py` | `server/modules/stock/analysis.py` | 提取 calc_rsi/calc_ma/analyze_ticker |

不迁移交易执行相关文件 (order_manager, strategy 等)。

## 实施步骤

### Step 1: 项目骨架
- 更新 `pyproject.toml` 添加所有后端依赖，`uv sync`
- `npm create vite` 创建 web/ 目录，安装前端依赖，配置 TailwindCSS
- 创建 `server/main.py` (FastAPI + CORS + /api/health)
- 创建 `server/config.py` (pydantic-settings)
- 创建 `.env.example` 和 `start.sh`

### Step 2: 核心框架 + 模块系统
- 实现 `server/core/llm.py` 和 `server/core/schemas.py`
- 实现 `server/modules/base.py` (BaseModule) 和 `server/modules/registry.py` (ModuleRegistry)
- 实现 `server/api/admin.py` 管理 API
- 创建 `data/modules_config.json`

### Step 3: Agent 系统 + 聊天
- 实现 `server/agent/state.py`, `router.py`, `graph.py`
- 实现 `server/api/chat.py` SSE 端点
- 前端: AppLayout + ChatPanel + MessageList + ChatInput + SSE 消费

### Step 4: 股票模块后端
- 迁移 6 个基础文件到 `server/modules/stock/`
- 实现 `service.py`, `tools.py`, `module.py`
- 实现 `server/agent/nodes/stock_agent.py`
- 更新 graph.py 添加 stock 路由
- 实现 `server/api/modules/stock.py` REST 端点

### Step 5: 股票模块前端
- 实现 Zustand stores (moduleStore, stockStore)
- 实现 ModulePanel 动态渲染
- 实现 StockModulePage (tab 容器)
- 实现 PortfolioView + PositionTable + FundsCard
- 实现 StockChart (Recharts 走势图 + MA + RSI)
- 实现 OptionsChainView
- 实现 AnalysisView

### Step 6: 管理页面
- 实现 AdminPage + ModuleManager + ModuleConfigForm

## 验证方案

1. `start.sh` 一键启动前后端
2. 访问 `http://localhost:5173`，左侧聊天框可与 DeepSeek 对话
3. 输入"帮我看看我的持仓" → 右侧渲染持仓表格
4. 输入"AAPL 走势" → 右侧切换到走势图
5. 输入"看看期权" → 右侧显示期权链
6. 访问 `/admin` → 可管理模块启停和配置
7. FutuOpenD 未运行时，yfinance 数据仍可正常展示走势和期权

## 关键依赖版本

**后端 (pyproject.toml)**:
fastapi, uvicorn[standard], langchain, langchain-openai, langgraph, futu-api, yfinance, pandas, numpy, python-dotenv, pydantic-settings

**前端 (package.json)**:
react, react-dom, react-router-dom, typescript, vite, @vitejs/plugin-react, tailwindcss, postcss, autoprefixer, recharts, zustand, lucide-react
