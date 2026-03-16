# 股价存储模块实现计划

## Context

当前系统通过 yfinance 实时获取股价数据，存在两个核心问题：
1. **限流严重**：yfinance 免费 API 频繁触发 429 Too Many Requests
2. **数据不持久**：查询过的股价没有存储，无法做长期趋势分析

本方案引入股价存储能力：DB 持久化股价 + 后台定时抓取 + watchlist 关注列表管理，作为现有 stock 模块的数据增强层。

**架构决策**：扩展现有 StockModule（非独立模块），避免 router 意图路由混淆。stock_store 包作为纯数据服务层，3 个新 tools 注册到 stock 模块。

---

## 文件变更总览

### 新建文件
| 文件 | 用途 |
|---|---|
| `server/modules/stock_store/__init__.py` | 包初始化 |
| `server/modules/stock_store/models.py` | 3 个 ORM 模型定义 |
| `server/modules/stock_store/repository.py` | DB CRUD 封装 |
| `server/modules/stock_store/service.py` | 业务逻辑层（DB-first 查询、watchlist CRUD） |
| `server/modules/stock_store/fetcher.py` | 后台价格抓取守护线程 |
| `server/modules/stock/watchlist_tools.py` | 3 个新 LangChain tools |

### 修改文件
| 文件 | 变更 |
|---|---|
| `server/db/session.py` | `init_db()` 增加新模型 import |
| `server/modules/stock/module.py` | 扩展 tools、system_prompt、on_enable/on_disable、default_config |
| `server/modules/stock/quote.py` | `fetch_quotes_batch` 集成 DB-first 查询 |
| `server/main.py` | lifespan 中启动时调用已启用模块的 `on_enable()` |
| `server/db/service.py` | AVAILABLE_SCOPES 可选追加 |

---

## 实现步骤

### Step 1: ORM 模型 — `server/modules/stock_store/models.py`

使用与全局 models 相同的 `Base`，单独文件放在 stock_store 包中（通过 init_db import 触发注册）。

```python
# 3 个表：

class WatchlistItem(Base):
    __tablename__ = "watchlist"
    id          = Column(Integer, PK)
    ticker      = Column(String(20), not null)      # "AAPL"
    market      = Column(String(10), default="US")   # "US" / "HK"
    display_name = Column(String(100), nullable)     # "苹果"
    created_at  = Column(DateTime)
    # UniqueConstraint("ticker", "market")

class StockDailyPrice(Base):
    __tablename__ = "stock_daily_prices"
    id       = Column(Integer, PK)
    ticker   = Column(String(20), not null)
    market   = Column(String(10), not null)
    date     = Column(String(10), not null)   # "2024-01-15"
    open     = Column(Float)
    high     = Column(Float)
    low      = Column(Float)
    close    = Column(Float)
    volume   = Column(BigInteger)
    created_at = Column(DateTime)
    # UniqueConstraint("ticker", "market", "date")
    # Index on (ticker, market, date)

class StockLatestQuote(Base):
    __tablename__ = "stock_latest_quotes"
    id              = Column(Integer, PK)
    ticker          = Column(String(20), not null)
    market          = Column(String(10), not null)
    regular_price   = Column(Float)
    regular_change  = Column(Float)
    regular_change_pct = Column(Float)
    pre_price       = Column(Float)
    pre_change      = Column(Float)
    pre_change_pct  = Column(Float)
    post_price      = Column(Float)
    post_change     = Column(Float)
    post_change_pct = Column(Float)
    prev_close      = Column(Float)
    session         = Column(String(20))    # "盘前"/"盘中"/"盘后"/"休市"
    updated_at      = Column(DateTime)
    # UniqueConstraint("ticker", "market")
```

**时间粒度**：日线（1d）。原因：yfinance 免费分钟线仅保留 7 天，日线足够 MA/RSI 分析，存储量可控（每只股票约 252 条/年）。

### Step 2: 建表注册 — `server/db/session.py`

`init_db()` 中新增 import：
```python
from server.modules.stock_store.models import WatchlistItem, StockDailyPrice, StockLatestQuote  # noqa: F401
```

### Step 3: Repository — `server/modules/stock_store/repository.py`

遵循 `server/db/repositories.py` 的模式：构造函数接收 `Session`。

**WatchlistRepository**
- `get_all() -> list[WatchlistItem]`
- `get_by_ticker(ticker, market) -> WatchlistItem | None`
- `add(ticker, market, display_name) -> WatchlistItem` — 存在则忽略
- `remove(ticker, market) -> bool`
- `to_dict(obj) -> dict`

**StockDailyPriceRepository**
- `get_latest(ticker, market, limit=30) -> list[StockDailyPrice]` — 按 date DESC
- `get_latest_date(ticker, market) -> str | None` — 最新已存日期
- `bulk_upsert(records: list[dict])` — 批量写入，跳过已存在的 (ticker, market, date)
- `to_dict(obj) -> dict`

**StockLatestQuoteRepository**
- `get(ticker, market) -> StockLatestQuote | None`
- `get_for_tickers(tickers, market) -> list[StockLatestQuote]`
- `upsert(ticker, market, **quote_fields) -> StockLatestQuote`
- `bulk_upsert(market, quotes_dict: dict[str, dict])` — 批量更新
- `to_dict(obj) -> dict`

### Step 4: Service — `server/modules/stock_store/service.py`

单例 `get_stock_store_service()`，管理 session 生命周期。

**核心方法**：

```python
class StockStoreService:
    # ── Watchlist ──
    def get_watchlist() -> list[dict]            # 含最新报价
    def add_to_watchlist(ticker, market, name) -> dict
    def remove_from_watchlist(ticker, market) -> bool

    # ── 价格查询（DB-first）──
    def get_latest_quotes(tickers, market) -> dict[str, dict]
        """先查 stock_latest_quotes 表，返回 {ticker: quote_dict}"""

    def get_daily_prices(ticker, market, days=30) -> list[dict]
        """查 stock_daily_prices 表，按 date DESC"""

    # ── 数据写入（供 fetcher 和 quote.py 调用）──
    def save_latest_quotes(market, quotes_dict)
        """将 fetch_quotes_batch 返回的 dict 写入 stock_latest_quotes"""

    def save_daily_prices(ticker, market, history_data)
        """将 yfinance history 写入 stock_daily_prices，跳过已有日期"""

    # ── DB-first + fallback（核心方法，供跨模块集成）──
    def get_quotes_with_fallback(tickers, market) -> dict[str, dict]
        """1) 查 DB  2) 对过期/缺失 ticker 调 yfinance  3) 回填 DB"""

    def get_daily_prices_with_fallback(ticker, market, days=30) -> dict
        """1) 查 DB 日线  2) 不足则补充 yfinance  3) 回填 DB"""
```

**过期判定**：`stock_latest_quotes.updated_at` 距今超过 `fetch_interval_minutes` 视为过期，fallback 到 yfinance。时间统一 UTC。

### Step 5: 后台 Fetcher — `server/modules/stock_store/fetcher.py`

参照 `server/channels/registry.py` 线程模式：

```python
class StockPriceFetcher:
    def __init__(self, interval_minutes=30):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        """创建 daemon 线程，立即执行首次抓取，然后进入定时循环"""
        self._thread = threading.Thread(target=self._run, daemon=True, name="stock-price-fetcher")
        self._thread.start()

    def _run(self):
        while not self._stop_event.is_set():
            self._fetch_cycle()
            self._stop_event.wait(self._interval_seconds)

    def _fetch_cycle(self):
        """单次抓取逻辑"""
        # 1. 从 DB 读 watchlist
        # 2. 分批调 fetch_quotes_batch（每批 5-10 只，批间 sleep 2s 避免限流）
        # 3. 写入 stock_latest_quotes
        # 4. 对每只 ticker 检查日线数据缺口，补充 yfinance history
        # 5. 写入 stock_daily_prices

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def is_running(self) -> bool
```

**限流保护**：批量抓取时每 5-10 只一批，批间 `time.sleep(2)`。复用 `quote.py` 现有的 `_yf_lock` 串行化。

### Step 6: 扩展 StockModule — `server/modules/stock/module.py`

```python
class StockModule(BaseModule):
    default_config = {
        # ...existing config...
        "fetch_interval_minutes": 30,     # 后台抓取间隔
        "watchlist_default_market": "US", # 默认市场
    }

    def get_tools(self):
        from .tools import get_portfolio, get_stock_trend, get_options_chain, get_portfolio_analysis
        from .watchlist_tools import list_watchlist, manage_watchlist, analyze_stock_from_db
        return [get_portfolio, get_stock_trend, get_options_chain, get_portfolio_analysis,
                list_watchlist, manage_watchlist, analyze_stock_from_db]

    def get_system_prompt(self):
        # 在现有 prompt 基础上追加 watchlist 工具说明
        return existing_prompt + """
5. 查看关注列表及最新价格 - 使用 list_watchlist 工具
6. 添加/删除关注的股票 - 使用 manage_watchlist 工具
7. 基于存储数据分析股票走势 - 使用 analyze_stock_from_db 工具

规则补充：
- 当用户想看关注的股票时，调用 list_watchlist
- 当用户要添加或删除关注股票时，调用 manage_watchlist
- 当用户要分析某只股票的走势时，优先用 analyze_stock_from_db（使用存储数据）"""

    def on_enable(self):
        """启动后台价格抓取"""
        config = get_stock_config()
        interval = config.get("fetch_interval_minutes", 30)
        self._fetcher = StockPriceFetcher(interval_minutes=interval)
        self._fetcher.start()

    def on_disable(self):
        """停止后台抓取"""
        if hasattr(self, "_fetcher") and self._fetcher:
            self._fetcher.stop()
```

### Step 7: 启动时触发 on_enable — `server/main.py`

当前 `discover_modules()` 只注册但不调用 `on_enable()`。需在 lifespan 中增加：

```python
registry = get_registry()
registry.discover_modules()
# 新增：对已启用模块调用 on_enable（启动 fetcher 等后台任务）
for module in registry.get_enabled_modules():
    try:
        module.on_enable()
    except Exception as e:
        logger.warning(f"模块启动失败 {module.module_id}: {e}")
```

同理，在 `yield` 后的 shutdown 阶段加：
```python
for module in registry.get_enabled_modules():
    try:
        module.on_disable()
    except Exception:
        pass
```

### Step 8: 新 Tools — `server/modules/stock/watchlist_tools.py`

**Tool 1: `list_watchlist`**
```python
@tool
def list_watchlist() -> dict:
    """列举关注列表中所有股票及其最新价格（含盘前、盘后行情）。"""
    # 调用 stock_store.service.get_watchlist()
    # IM 通道：返回文字数据
    # Web 通道：返回 _ui_command: {module: "stock", action: "show_watchlist"}
```

**Tool 2: `manage_watchlist`**
```python
@tool
def manage_watchlist(action: str, ticker: str, market: str = "US", display_name: str = "") -> dict:
    """添加或删除关注列表中的股票。action 为 'add' 或 'remove'，ticker 为股票代码如 AAPL。"""
    # action="add": 添加到 watchlist + 立即拉取历史数据回填 DB
    # action="remove": 从 watchlist 删除
```

**Tool 3: `analyze_stock_from_db`**
```python
@tool
def analyze_stock_from_db(ticker: str, days: int = 30) -> dict:
    """基于数据库存储的历史数据分析股票走势，包含MA均线、RSI等技术指标。如果数据不足会自动补充。"""
    # 1. 调 stock_store.service.get_daily_prices_with_fallback()
    # 2. 复用 analysis.py 的 calc_rsi(), calc_ma(), calc_ma_series()
    # 3. 返回技术分析结果
    # Web 通道附带 _ui_command: {module: "stock", action: "show_trend"}
```

### Step 9: 跨模块 DB-first 集成 — `server/modules/stock/quote.py`

修改 `fetch_quotes_batch()` 增加可选 DB 缓存层：

```python
def fetch_quotes_batch(tickers, market="US"):
    # === 新增：尝试从 stock_store DB 获取 ===
    try:
        from server.modules.stock_store.service import get_stock_store_service
        svc = get_stock_store_service()
        db_quotes = svc.get_latest_quotes(tickers, market)
        interval = _get_fetch_interval()  # 从 stock config 读
        # 过滤出 DB 中存在且未过期的 tickers
        fresh, stale = _partition_fresh(db_quotes, interval)
        if not stale:
            return fresh  # 全部命中 DB
        # 仅对过期/缺失的 ticker 调 yfinance
        tickers = list(stale)
    except ImportError:
        fresh = {}
    except Exception:
        fresh = {}

    # === 原有 yfinance 逻辑（仅查缺失部分）===
    ...existing yfinance code...

    # === 新增：回填 DB ===
    try:
        svc.save_latest_quotes(market, yf_quotes)
    except Exception:
        pass

    return {**fresh, **yf_quotes}
```

使用 `try/except ImportError` 实现松耦合——stock_store 不可用时完全降级到原逻辑。

---

## 关键设计约束

1. **SQLite 并发**：fetcher 线程和 agent tool 都写 DB。每次操作使用独立 session 并及时 close，避免 "database is locked"
2. **yfinance 限流**：fetcher 分批抓取（每批 5-10 只，批间 sleep 2s），复用 `_yf_lock`
3. **watchlist 添加时立即回填**：新增股票到 watchlist 时同步拉取最近 30 天日线数据，不等下个 fetcher 周期
4. **时间统一 UTC**：所有 `created_at`/`updated_at` 使用 `datetime.now(timezone.utc)`，与现有 models.py 的 `_utcnow()` 一致

---

## 验证方案

1. **启动验证**：`uv run python -m server.main`，确认日志输出 fetcher 启动信息
2. **建表验证**：检查 `data/app.db` 中 3 个新表已创建（`watchlist`, `stock_daily_prices`, `stock_latest_quotes`）
3. **对话测试**：通过 chat 接口测试：
   - "帮我把 AAPL 加入关注列表" → manage_watchlist(add) 被调用
   - "看看关注列表" → list_watchlist 返回含最新报价
   - "分析 AAPL 走势" → analyze_stock_from_db 返回含 MA/RSI
   - "把 AAPL 从关注列表删除" → manage_watchlist(remove) 被调用
4. **后台抓取验证**：等待一个 fetch 周期后查 DB，确认 stock_daily_prices 和 stock_latest_quotes 有数据写入
5. **DB-first 验证**：在有 DB 数据的情况下调用 get_portfolio，观察日志确认走 DB 路径而非 yfinance
