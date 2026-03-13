import { useEffect, useState } from 'react';
import { useStockStore, type TrendData } from '../../stores/stockStore';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area,
} from 'recharts';
import { Loader2, RefreshCw } from 'lucide-react';

/* ---------- single ticker chart card ---------- */

function TickerChartCard({
  ticker,
  data,
  isLoading,
}: {
  ticker: string;
  data: TrendData | undefined;
  isLoading: boolean;
}) {
  if (isLoading && !data) {
    return (
      <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 p-6 mb-4">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">{ticker} 走势加载中...</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 p-4 mb-4">
        <span className="text-sm font-semibold text-gray-800">{ticker}</span>
        <span className="text-sm text-gray-400 ml-2">暂无走势数据</span>
      </div>
    );
  }

  const chartData = data.closes.map((close, i) => ({
    date: data.dates?.[i] || `Day ${i + 1}`,
    close: Number(close.toFixed(2)),
    ma5: data.ma5[i] != null ? Number(Number(data.ma5[i]).toFixed(2)) : undefined,
    ma20: data.ma20[i] != null ? Number(Number(data.ma20[i]).toFixed(2)) : undefined,
  }));

  // generate a unique gradient id per ticker
  const gradientId = `closeGrad_${ticker}`;

  return (
    <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 p-5 mb-4">
      {/* header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-baseline gap-3">
          <h3 className="text-base font-bold text-gray-900">{ticker}</h3>
          {data.current_price != null && (
            <span className="text-lg font-bold font-num text-gray-900">
              ${data.current_price.toFixed(2)}
            </span>
          )}
          {data.price_change_5d_pct != null && (
            <span
              className={`text-sm font-semibold font-num ${
                data.price_change_5d_pct >= 0 ? 'text-emerald-600' : 'text-red-600'
              }`}
            >
              {data.price_change_5d_pct >= 0 ? '+' : ''}
              {data.price_change_5d_pct}%
              <span className="text-xs font-normal text-gray-400 ml-1">5日</span>
            </span>
          )}
        </div>
        {isLoading && (
          <Loader2 className="w-4 h-4 text-gray-300 animate-spin" />
        )}
      </div>

      {/* chart */}
      <ResponsiveContainer width="100%" height={260}>
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
            tickFormatter={(v) => v.slice(5)}
            axisLine={{ stroke: '#e5e7eb' }}
            tickLine={false}
            interval={Math.max(0, Math.floor(chartData.length / 6) - 1)}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            domain={['auto', 'auto']}
            tickFormatter={(v) => `$${v}`}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 10,
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
              padding: '8px 12px',
            }}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = { close: '收盘价', ma5: 'MA5', ma20: 'MA20' };
              return [`$${value}`, labels[name] || name];
            }}
            labelFormatter={(label) => label}
          />
          <Area
            type="monotone"
            dataKey="close"
            fill={`url(#${gradientId})`}
            stroke="#3b82f6"
            strokeWidth={2}
          />
          <Line type="monotone" dataKey="ma5" stroke="#f59e0b" strokeWidth={1.5} dot={false} connectNulls />
          <Line type="monotone" dataKey="ma20" stroke="#ef4444" strokeWidth={1.5} dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>

      {/* legend */}
      <div className="flex items-center justify-center gap-5 mt-2 text-xs text-gray-400">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-blue-500 inline-block rounded" />收盘价
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-amber-500 inline-block rounded" />MA5
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-red-500 inline-block rounded" />MA20
        </span>
      </div>
    </div>
  );
}

/* ---------- main view ---------- */

export function StockChart() {
  const portfolio = useStockStore((s) => s.portfolio);
  const trends = useStockStore((s) => s.trends);
  const loading = useStockStore((s) => s.loading);
  const fetchTrend = useStockStore((s) => s.fetchTrend);
  const fetchPortfolio = useStockStore((s) => s.fetchPortfolio);
  const [fetched, setFetched] = useState(false);

  const tickers = portfolio?.positions.map((p) => p.ticker) ?? [];

  // Auto-fetch portfolio if not yet loaded
  useEffect(() => {
    if (!portfolio) fetchPortfolio();
  }, [portfolio, fetchPortfolio]);

  // Auto-fetch trend for every holding once portfolio is available
  useEffect(() => {
    if (tickers.length === 0 || fetched) return;
    setFetched(true);
    tickers.forEach((t) => {
      if (!trends[t]) {
        fetchTrend(t);
      }
    });
  }, [tickers.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefreshAll = () => {
    setFetched(false);
    tickers.forEach((t) => fetchTrend(t));
  };

  if (!portfolio) {
    return (
      <div className="flex items-center gap-2 text-gray-400 py-20 justify-center">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">加载持仓数据...</span>
      </div>
    );
  }

  if (tickers.length === 0) {
    return <div className="text-center text-gray-400 py-16 text-sm">暂无持仓</div>;
  }

  const anyLoading = tickers.some((t) => loading[`trend_${t}`]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-700">
          持仓走势（{tickers.length} 只）
        </h2>
        <button
          onClick={handleRefreshAll}
          disabled={anyLoading}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${anyLoading ? 'animate-spin' : ''}`} />
          刷新全部
        </button>
      </div>

      {tickers.map((ticker) => (
        <TickerChartCard
          key={ticker}
          ticker={ticker}
          data={trends[ticker]}
          isLoading={!!loading[`trend_${ticker}`]}
        />
      ))}
    </div>
  );
}
