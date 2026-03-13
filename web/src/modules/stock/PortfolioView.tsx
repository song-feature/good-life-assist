import { useCallback, useEffect, useRef, useState } from 'react';
import { useStockStore, type Position, type Funds } from '../../stores/stockStore';
import { DollarSign, TrendingUp, TrendingDown, Wallet, RefreshCw, AlertTriangle, Loader2 } from 'lucide-react';

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

function PositionTable({ positions }: { positions: Position[] }) {
  if (!positions.length) {
    return <div className="text-center text-gray-400 py-8">暂无持仓数据</div>;
  }

  return (
    <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50/80 text-gray-500 text-xs uppercase tracking-wider">
            <th className="text-left px-4 py-3 font-semibold">代码</th>
            <th className="text-left px-4 py-3 font-semibold">名称</th>
            <th className="text-right px-4 py-3 font-semibold">数量</th>
            <th className="text-right px-4 py-3 font-semibold">成本价</th>
            <th className="text-right px-4 py-3 font-semibold">现价</th>
            <th className="text-right px-4 py-3 font-semibold">盈亏</th>
            <th className="text-right px-4 py-3 font-semibold">盈亏%</th>
            <th className="text-right px-4 py-3 font-semibold">今日盈亏</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {positions.map((pos, i) => {
            const plColor = pos.pl_val >= 0 ? 'text-emerald-600' : 'text-red-600';
            const todayColor = pos.today_pl_val >= 0 ? 'text-emerald-600' : 'text-red-600';
            return (
              <tr key={pos.ticker} className={`hover:bg-blue-50/30 transition-colors ${i % 2 === 1 ? 'bg-gray-50/30' : ''}`}>
                <td className="px-4 py-3 font-semibold text-gray-900">{pos.ticker}</td>
                <td className="px-4 py-3 text-gray-500">{pos.name}</td>
                <td className="px-4 py-3 text-right font-num text-gray-700">{pos.qty}</td>
                <td className="px-4 py-3 text-right font-num text-gray-700">${pos.cost_price?.toFixed(2)}</td>
                <td className="px-4 py-3 text-right font-num font-semibold text-gray-900">${pos.current_price?.toFixed(2)}</td>
                <td className={`px-4 py-3 text-right font-num font-semibold ${plColor}`}>
                  {pos.pl_val >= 0 ? '+' : ''}${fmt(pos.pl_val)}
                </td>
                <td className={`px-4 py-3 text-right font-num font-semibold ${plColor}`}>
                  {pos.pl_ratio >= 0 ? '+' : ''}{pos.pl_ratio?.toFixed(2)}%
                </td>
                <td className={`px-4 py-3 text-right font-num font-semibold ${todayColor}`}>
                  {pos.today_pl_val >= 0 ? '+' : ''}${fmt(pos.today_pl_val)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
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
