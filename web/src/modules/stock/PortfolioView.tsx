import { useCallback, useEffect, useRef, useState } from 'react';
import { useStockStore, type Position, type Funds } from '../../stores/stockStore';
import { DollarSign, TrendingUp, TrendingDown, Wallet, RefreshCw, AlertTriangle, Loader2, Sparkles, X } from 'lucide-react';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area,
} from 'recharts';

const REFRESH_INTERVAL = 10; // seconds

const fmt = (v: number) =>
  v?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—';

function FundsCard({ funds, todayPl }: { funds: Funds | null; todayPl: number }) {
  if (!funds) return null;

  const cards = [
    { label: '总资产', value: funds.total_assets, icon: DollarSign, bg: 'bg-blue-50', iconColor: 'text-blue-500' },
    { label: '持仓市值', value: funds.market_val, icon: TrendingUp, bg: 'bg-indigo-50', iconColor: 'text-indigo-500' },
    { label: '可用现金', value: funds.cash, icon: Wallet, bg: 'bg-emerald-50', iconColor: 'text-emerald-500' },
    {
      label: '今日盈亏', value: todayPl,
      icon: todayPl >= 0 ? TrendingUp : TrendingDown,
      bg: todayPl >= 0 ? 'bg-emerald-50' : 'bg-red-50',
      iconColor: todayPl >= 0 ? 'text-emerald-500' : 'text-red-500',
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-3 mb-5">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div key={card.label} className="bg-white rounded-xl p-4 shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80">
            <div className="flex items-center gap-2 mb-2">
              <div className={`w-7 h-7 rounded-lg ${card.bg} flex items-center justify-center`}>
                <Icon className={`w-3.5 h-3.5 ${card.iconColor}`} />
              </div>
              <span className="text-xs text-gray-500 font-medium">{card.label}</span>
            </div>
            <div className={`text-lg font-bold font-num ${
              card.label === '今日盈亏'
                ? card.value >= 0 ? 'text-emerald-600' : 'text-red-600'
                : 'text-gray-900'
            }`}>
              ${fmt(card.value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SessionBadge({ session }: { session?: string }) {
  if (!session) return null;
  const cfg: Record<string, { color: string; dot: string }> = {
    '盘中': { color: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500 animate-pulse' },
    '盘前': { color: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' },
    '盘后': { color: 'bg-blue-50 text-blue-700', dot: 'bg-blue-500' },
    '休市': { color: 'bg-gray-100 text-gray-500', dot: 'bg-gray-400' },
  };
  const c = cfg[session] ?? { color: 'bg-gray-100 text-gray-500', dot: 'bg-gray-400' };
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${c.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {session}
    </span>
  );
}

/* ---------- Trend Dialog ---------- */

const PERIOD_TABS = [
  { key: '1d', label: '24小时' },
  { key: '5d', label: '5天' },
  { key: '1mo', label: '1月' },
  { key: '3mo', label: '3月' },
  { key: '6mo', label: '6月' },
  { key: '1y', label: '1年' },
  { key: 'ytd', label: 'YTD' },
] as const;

function TrendDialog({ ticker, session, onClose }: { ticker: string; session?: string; onClose: () => void }) {
  const trends = useStockStore((s) => s.trends);
  const loading = useStockStore((s) => s.loading);
  const fetchTrend = useStockStore((s) => s.fetchTrend);
  const [period, setPeriod] = useState('1d');

  const key = `${ticker}:${period}`;
  const trendData = trends[key];
  const isLoading = !!loading[`trend_${key}`];

  // Fetch data on mount and tab switch
  useEffect(() => {
    fetchTrend(ticker, period);
  }, [ticker, period, fetchTrend]);

  // Auto-refresh: 10s interval when session=盘中 and period is 1d or 5d
  const shouldAutoRefresh = session === '盘中' && (period === '1d' || period === '5d');

  useEffect(() => {
    if (!shouldAutoRefresh) return;
    const id = setInterval(() => {
      fetchTrend(ticker, period);
    }, 10_000);
    return () => clearInterval(id);
  }, [shouldAutoRefresh, ticker, period, fetchTrend]);

  // ESC to close
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Chart data
  const chartData = trendData
    ? trendData.closes.map((close, i) => ({
        date: trendData.dates?.[i] || `D${i + 1}`,
        close: Number(close.toFixed(2)),
        ma5: trendData.ma5[i] != null ? Number(Number(trendData.ma5[i]).toFixed(2)) : undefined,
        ma20: trendData.ma20[i] != null ? Number(Number(trendData.ma20[i]).toFixed(2)) : undefined,
      }))
    : [];

  const isIntraday = trendData?.dates?.[0]?.includes(' ') ?? false;
  const gradientId = `dlgGrad_${ticker}`;

  const formatXAxis = (v: string) => {
    if (isIntraday) {
      const parts = v.split(' ');
      return parts[1] || v;
    }
    return v.slice(5);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-[720px] w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-gray-900">{ticker}</span>
            {trendData?.current_price != null && (
              <span className="text-lg font-bold font-num text-gray-900">${trendData.current_price.toFixed(2)}</span>
            )}
            {trendData?.price_change_5d_pct != null && (
              <span className={`text-sm font-semibold font-num ${trendData.price_change_5d_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {trendData.price_change_5d_pct >= 0 ? '+' : ''}{trendData.price_change_5d_pct}%
              </span>
            )}
            <SessionBadge session={session} />
            {shouldAutoRefresh && (
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                实时刷新中
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Period tabs */}
        <div className="flex items-center gap-1 px-6 pb-3">
          {PERIOD_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setPeriod(tab.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 ${
                period === tab.key
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Chart */}
        <div className="px-6 pb-2">
          {isLoading && !trendData ? (
            <div className="flex items-center gap-2 text-gray-400 h-[320px] justify-center">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">加载走势数据...</span>
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  tickFormatter={formatXAxis}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                  interval={Math.max(0, Math.floor(chartData.length / 6) - 1)}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  domain={['auto', 'auto']}
                  tickFormatter={(v: number) => `$${v}`}
                  axisLine={false}
                  tickLine={false}
                  width={60}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 12, borderRadius: 10, border: '1px solid #e5e7eb',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)', padding: '8px 12px',
                  }}
                  formatter={(value: number, name: string) => {
                    const labels: Record<string, string> = { close: '价格', ma5: 'MA5', ma20: 'MA20' };
                    return [`$${value}`, labels[name] || name];
                  }}
                  labelFormatter={(label: string) => label}
                />
                <Area type="monotone" dataKey="close" fill={`url(#${gradientId})`} stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="ma5" stroke="#f59e0b" strokeWidth={1.5} dot={false} connectNulls />
                <Line type="monotone" dataKey="ma20" stroke="#ef4444" strokeWidth={1.5} dot={false} connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[320px] text-sm text-gray-400">暂无走势数据</div>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center justify-center gap-5 pb-5 text-xs text-gray-400">
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-blue-500 inline-block rounded" />价格</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-amber-500 inline-block rounded" />MA5</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-red-500 inline-block rounded" />MA20</span>
        </div>
      </div>
    </div>
  );
}

/* ---------- Ticker Cell (click to open dialog) ---------- */

function TickerCell({ ticker, onOpen }: { ticker: string; onOpen: (ticker: string) => void }) {
  return (
    <td className="px-4 py-3 font-semibold text-gray-900">
      <button
        onClick={() => onOpen(ticker)}
        className="border-b border-dashed border-gray-300 hover:border-blue-400 hover:text-blue-600 transition-colors cursor-pointer"
      >
        {ticker}
      </button>
    </td>
  );
}

function PositionTable({ positions }: { positions: Position[] }) {
  const [openTicker, setOpenTicker] = useState<string | null>(null);

  if (!positions.length) {
    return <div className="text-center text-gray-400 py-8">暂无持仓数据</div>;
  }

  // 取第一条持仓的 session 作为整体市场状态
  const marketSession = positions[0]?.session;

  return (
    <>
      <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 overflow-hidden">
        {/* 表格顶栏：交易时段标识 */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100/60 bg-gray-50/40">
          <span className="text-xs text-gray-400">持仓明细</span>
          <SessionBadge session={marketSession} />
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50/80 text-gray-500 text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3 font-semibold">代码</th>
              <th className="text-left px-4 py-3 font-semibold">名称</th>
              <th className="text-right px-4 py-3 font-semibold">数量</th>
              <th className="text-right px-4 py-3 font-semibold">成本价</th>
              <th className="text-right px-4 py-3 font-semibold">现价</th>
              <th className="text-right px-4 py-3 font-semibold">涨跌</th>
              <th className="text-right px-4 py-3 font-semibold">今日盈亏</th>
              <th className="text-right px-4 py-3 font-semibold">今日盈亏%</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {positions.map((pos, i) => {
              const chg = pos.price_change ?? 0;
              const chgPct = pos.price_change_pct ?? 0;
              const chgColor = chg > 0 ? 'text-emerald-600' : chg < 0 ? 'text-red-600' : 'text-gray-500';
              const todayColor = pos.today_pl_val >= 0 ? 'text-emerald-600' : 'text-red-600';
              return (
                <tr key={pos.ticker} className={`hover:bg-blue-50/30 transition-colors ${i % 2 === 1 ? 'bg-gray-50/30' : ''}`}>
                  <TickerCell ticker={pos.ticker} onOpen={setOpenTicker} />
                  <td className="px-4 py-3 text-gray-500">{pos.name}</td>
                  <td className="px-4 py-3 text-right font-num text-gray-700">{pos.qty}</td>
                  <td className="px-4 py-3 text-right font-num text-gray-700">${pos.cost_price?.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-num font-semibold text-gray-900">
                    ${pos.current_price?.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right font-num font-medium ${chgColor}`}>
                    <div className="flex flex-col items-end leading-tight">
                      <span>{chg > 0 ? '+' : ''}{chg.toFixed(2)}</span>
                      <span className="text-[11px]">{chgPct > 0 ? '+' : ''}{chgPct.toFixed(2)}%</span>
                    </div>
                  </td>
                  <td className={`px-4 py-3 text-right font-num font-semibold ${todayColor}`}>
                    {pos.today_pl_val >= 0 ? '+' : ''}${fmt(pos.today_pl_val)}
                  </td>
                  <td className={`px-4 py-3 text-right font-num font-semibold ${todayColor}`}>
                    {chgPct >= 0 ? '+' : ''}{chgPct.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {openTicker && (
        <TrendDialog
          ticker={openTicker}
          session={marketSession}
          onClose={() => setOpenTicker(null)}
        />
      )}
    </>
  );
}

function SignalBadge({ signal }: { signal: string }) {
  const config: Record<string, { label: string; color: string }> = {
    golden_cross: { label: '金叉', color: 'bg-emerald-100 text-emerald-700 ring-emerald-600/10' },
    death_cross: { label: '死叉', color: 'bg-red-100 text-red-700 ring-red-600/10' },
    neutral: { label: '中性', color: 'bg-gray-100 text-gray-700 ring-gray-600/10' },
    bullish: { label: '看涨', color: 'bg-emerald-100 text-emerald-700 ring-emerald-600/10' },
    bearish: { label: '看跌', color: 'bg-red-100 text-red-700 ring-red-600/10' },
    no_data: { label: '无数据', color: 'bg-gray-50 text-gray-400 ring-gray-400/10' },
    no_options: { label: '无期权', color: 'bg-gray-50 text-gray-400 ring-gray-400/10' },
  };
  const c = config[signal] || { label: signal, color: 'bg-gray-100 text-gray-600 ring-gray-600/10' };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-medium ring-1 ring-inset ${c.color}`}>
      {c.label}
    </span>
  );
}

function RSIGauge({ value }: { value: number | null }) {
  if (value == null) return <span className="text-xs text-gray-400">—</span>;
  const color = value > 70 ? 'text-red-600' : value < 30 ? 'text-emerald-600' : 'text-gray-800';
  const label = value > 70 ? '超买' : value < 30 ? '超卖' : '中性';
  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-sm font-bold font-num ${color}`}>{value}</span>
      <span className={`text-[10px] font-medium ${color} opacity-80`}>{label}</span>
    </div>
  );
}

function AnalysisSection() {
  const analysis = useStockStore((s) => s.analysis);
  const analysisLoading = useStockStore((s) => s.loading.analysis);
  const fetchAnalysis = useStockStore((s) => s.fetchAnalysis);
  const portfolio = useStockStore((s) => s.portfolio);

  useEffect(() => {
    if (portfolio && !analysis && !analysisLoading) {
      fetchAnalysis();
    }
  }, [portfolio]); // eslint-disable-line react-hooks/exhaustive-deps

  if (analysisLoading) {
    return (
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">分析建议</h2>
        <div className="flex items-center gap-2 text-gray-400 py-10 justify-center">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">分析数据加载中，请耐心等待...</span>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const holdings = (analysis.holdings || []) as Record<string, unknown>[];

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-700">分析建议</h2>
        <button
          onClick={fetchAnalysis}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-150"
        >
          <RefreshCw className="w-3 h-3" />
          刷新
        </button>
      </div>

      <RecommendationsBlock />

      <div className="space-y-3 mb-4">
        {holdings.map((h) => {
          const plVal = (h.pl_val as number) || 0;
          const plRatio = (h.pl_ratio as number) || 0;
          const plColor = plVal >= 0 ? 'text-emerald-600' : 'text-red-600';

          return (
            <div key={h.ticker as string} className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-gray-900">{h.ticker as string}</span>
                  <span className="text-xs text-gray-400">{h.name as string}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{h.qty as number} 股</span>
                  <span className={`text-xs font-semibold font-num ${plColor}`}>
                    {plVal >= 0 ? '+' : ''}${fmt(plVal)}
                    <span className="ml-1 opacity-75">({plRatio >= 0 ? '+' : ''}{plRatio.toFixed(2)}%)</span>
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div>
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider">MA 信号</span>
                  <div className="mt-1">
                    <SignalBadge signal={h.ma_signal as string} />
                  </div>
                </div>
                <div>
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider">RSI(14)</span>
                  <div className="mt-1">
                    <RSIGauge value={h.rsi14 as number | null} />
                  </div>
                </div>
                <div>
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider">5日涨跌</span>
                  <div className="mt-1">
                    {h.price_change_5d_pct != null ? (
                      <span className={`text-sm font-bold font-num ${
                        (h.price_change_5d_pct as number) >= 0 ? 'text-emerald-600' : 'text-red-600'
                      }`}>
                        {(h.price_change_5d_pct as number) >= 0 ? '+' : ''}{(h.price_change_5d_pct as number).toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider">期权情绪</span>
                  <div className="mt-1">
                    <SignalBadge signal={h.options_sentiment as string} />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-amber-50/80 border border-amber-200/60 rounded-xl p-3.5 flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
        <p className="text-xs text-amber-800 leading-relaxed">
          以上分析基于技术指标和期权数据，仅供参考。请结合基本面和市场环境综合判断。
        </p>
      </div>
    </div>
  );
}

/* ---------- Recommendations Block ---------- */

function renderSimpleMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

function RecommendationsBlock() {
  const analysis = useStockStore((s) => s.analysis);
  const recommendations = useStockStore((s) => s.analysisRecommendations);
  const isLoading = useStockStore((s) => s.loading.analysis_recommendations);
  const fetchReco = useStockStore((s) => s.fetchAnalysisRecommendations);
  const [triggered, setTriggered] = useState(false);

  useEffect(() => {
    if (analysis && !recommendations && !isLoading && !triggered) {
      setTriggered(true);
      fetchReco();
    }
  }, [analysis, recommendations, isLoading, triggered, fetchReco]);

  if (!analysis) return null;

  return (
    <div className="mb-4">
      <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100/60">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-gray-800">AI 投资建议</h3>
          </div>
          <button
            onClick={fetchReco}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-150 disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
        <div className="px-4 py-3">
          {isLoading && !recommendations ? (
            <div className="flex items-center gap-2 text-gray-400 py-6 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-xs">AI 正在生成投资建议...</span>
            </div>
          ) : recommendations ? (
            <div className="text-[13px] text-gray-700 leading-relaxed whitespace-pre-line">
              {recommendations.split('\n').map((line, i) => (
                <p key={i} className={line.trim() === '' ? 'h-2' : 'mb-1'}>
                  {renderSimpleMarkdown(line)}
                </p>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-400 text-xs py-4">暂无建议数据</div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------- Countdown refresh indicator ---------- */

function RefreshCountdown({
  countdown,
  isRefreshing,
  onManualRefresh,
}: {
  countdown: number;
  isRefreshing: boolean;
  onManualRefresh: () => void;
}) {
  const pct = ((REFRESH_INTERVAL - countdown) / REFRESH_INTERVAL) * 100;

  return (
    <div className="flex items-center gap-2.5">
      <button
        onClick={onManualRefresh}
        disabled={isRefreshing}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-150 disabled:opacity-50"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
        {isRefreshing ? '刷新中' : '刷新'}
      </button>

      {/* Countdown ring + text */}
      <div className="flex items-center gap-1.5">
        <div className="relative w-5 h-5">
          <svg className="w-5 h-5 -rotate-90" viewBox="0 0 20 20">
            <circle
              cx="10" cy="10" r="8"
              fill="none" stroke="#e5e7eb" strokeWidth="2"
            />
            <circle
              cx="10" cy="10" r="8"
              fill="none" stroke="#3b82f6" strokeWidth="2"
              strokeDasharray={`${2 * Math.PI * 8}`}
              strokeDashoffset={`${2 * Math.PI * 8 * (1 - pct / 100)}`}
              strokeLinecap="round"
              className="transition-[stroke-dashoffset] duration-1000 ease-linear"
            />
          </svg>
        </div>
        <span className="text-[11px] text-gray-400 font-num tabular-nums w-14">
          {countdown}s 后刷新
        </span>
      </div>
    </div>
  );
}

/* ---------- main ---------- */

export function PortfolioView() {
  const portfolio = useStockStore((s) => s.portfolio);
  const loading = useStockStore((s) => s.loading.portfolio);
  const fetchPortfolio = useStockStore((s) => s.fetchPortfolio);
  const fetchingRef = useRef(false);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL);
  const [refreshing, setRefreshing] = useState(false);

  const silentRefresh = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    setRefreshing(true);
    try {
      await fetchPortfolio();
    } finally {
      fetchingRef.current = false;
      setRefreshing(false);
    }
  }, [fetchPortfolio]);

  // Auto-refresh timer: tick every second, fire refresh when countdown reaches 0
  useEffect(() => {
    if (!portfolio) return;

    const id = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          silentRefresh();
          return REFRESH_INTERVAL;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(id);
  }, [portfolio, silentRefresh]);

  const handleManualRefresh = useCallback(() => {
    silentRefresh();
    setCountdown(REFRESH_INTERVAL);
  }, [silentRefresh]);

  if (!portfolio && !loading) {
    return (
      <div className="text-center text-gray-400 py-20">
        <p className="text-sm">等待 Agent 查询持仓数据...</p>
        <button
          onClick={fetchPortfolio}
          className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 text-sm bg-blue-600 text-white rounded-xl hover:bg-blue-700 shadow-sm hover:shadow transition-all duration-150"
        >
          <RefreshCw className="w-4 h-4" />
          手动刷新
        </button>
      </div>
    );
  }

  if (loading && !portfolio) {
    return (
      <div className="flex items-center gap-2 text-gray-400 py-20 justify-center">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">加载中...</span>
      </div>
    );
  }

  return (
    <div>
      {/* Refresh countdown bar */}
      <div className="flex items-center justify-end mb-3">
        <RefreshCountdown
          countdown={countdown}
          isRefreshing={refreshing}
          onManualRefresh={handleManualRefresh}
        />
      </div>

      <FundsCard funds={portfolio?.funds ?? null} todayPl={portfolio?.today_pl_total ?? 0} />
      <PositionTable positions={portfolio?.positions ?? []} />
      <AnalysisSection />
    </div>
  );
}
