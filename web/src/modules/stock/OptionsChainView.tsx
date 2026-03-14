import { useEffect, useState } from 'react';
import { useStockStore, type OptionsWallData, type WallAnalysis } from '../../stores/stockStore';
import { Loader2, RefreshCw, ShieldAlert, TrendingUp } from 'lucide-react';

/* ---------- Wall mini-table for one expiry ---------- */

function WallExpiryBlock({ label, wall }: { label: string; wall: WallAnalysis | null }) {
  if (!wall) {
    return (
      <div className="flex-1 bg-gray-50/50 rounded-lg p-3">
        <span className="text-xs text-gray-400">{label}：无数据</span>
      </div>
    );
  }

  const fmtOI = (v: number) => v?.toLocaleString() ?? '0';

  return (
    <div className="flex-1 bg-gray-50/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-gray-700">{label}</span>
        <span className="text-[10px] text-gray-400">{wall.expiry_date}</span>
      </div>

      {/* Call wall */}
      <div className="mb-2">
        <span className="text-[10px] text-red-500 font-medium uppercase tracking-wider">Call Wall (阻力)</span>
        <div className="mt-1 space-y-0.5">
          {wall.call_walls.slice(0, 3).map((w, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="font-num font-medium text-gray-800">${w.strike.toFixed(2)}</span>
              <span className="font-num text-gray-500">OI: {fmtOI(w.openInterest)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Put wall */}
      <div className="mb-2">
        <span className="text-[10px] text-emerald-600 font-medium uppercase tracking-wider">Put Wall (支撑)</span>
        <div className="mt-1 space-y-0.5">
          {wall.put_walls.slice(0, 3).map((w, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="font-num font-medium text-gray-800">${w.strike.toFixed(2)}</span>
              <span className="font-num text-gray-500">OI: {fmtOI(w.openInterest)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Max Pain & P/C */}
      <div className="flex items-center gap-3 pt-1.5 border-t border-gray-200/60 text-xs">
        <span className="text-gray-500">
          Max Pain: <b className="text-gray-800 font-num">${wall.max_pain?.toFixed(2) ?? '—'}</b>
        </span>
        <span className="text-gray-500">
          P/C: <b className={`font-num ${wall.put_call_ratio > 1 ? 'text-red-600' : wall.put_call_ratio < 0.7 ? 'text-emerald-600' : 'text-gray-800'}`}>
            {wall.put_call_ratio.toFixed(2)}
          </b>
        </span>
      </div>
    </div>
  );
}

/* ---------- Wall card per ticker ---------- */

function OptionsWallCard({
  ticker,
  wallData,
  summary,
  isLoadingWall,
  isLoadingSummary,
}: {
  ticker: string;
  wallData: OptionsWallData | undefined;
  summary: string | undefined;
  isLoadingWall: boolean;
  isLoadingSummary: boolean;
}) {
  if (isLoadingWall && !wallData) {
    return (
      <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 p-5 mb-3">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">{ticker} 期权墙分析中...</span>
        </div>
      </div>
    );
  }

  if (!wallData || (!wallData.this_friday && !wallData.next_friday)) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] border border-gray-100/80 p-5 mb-3">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <ShieldAlert className="w-4 h-4 text-indigo-500" />
        <h3 className="text-sm font-bold text-gray-900">{ticker} 期权墙</h3>
        {wallData.current_price != null && (
          <span className="text-xs text-gray-400 font-num">当前 ${wallData.current_price.toFixed(2)}</span>
        )}
        {isLoadingWall && <Loader2 className="w-3.5 h-3.5 text-gray-300 animate-spin" />}
      </div>

      {/* Two-column wall display */}
      <div className="flex gap-3 mb-3">
        <WallExpiryBlock label="本周五" wall={wallData.this_friday} />
        <WallExpiryBlock label="下周五" wall={wallData.next_friday} />
      </div>

      {/* AI Summary */}
      {(isLoadingSummary || summary) && (
        <div className="bg-blue-50/60 rounded-lg p-3 mt-2">
          <div className="flex items-start gap-2">
            <TrendingUp className="w-3.5 h-3.5 text-blue-500 mt-0.5 shrink-0" />
            {isLoadingSummary && !summary ? (
              <div className="flex items-center gap-2 text-gray-400">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span className="text-xs">AI 分析中...</span>
              </div>
            ) : (
              <p className="text-xs text-gray-700 leading-relaxed">{summary}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Main view ---------- */

export function OptionsChainView() {
  const portfolio = useStockStore((s) => s.portfolio);
  const optionsWalls = useStockStore((s) => s.optionsWalls);
  const optionsWallSummaries = useStockStore((s) => s.optionsWallSummaries);
  const loading = useStockStore((s) => s.loading);
  const fetchOptionsWall = useStockStore((s) => s.fetchOptionsWall);
  const fetchOptionsWallSummary = useStockStore((s) => s.fetchOptionsWallSummary);
  const fetchPortfolio = useStockStore((s) => s.fetchPortfolio);
  const [fetched, setFetched] = useState(false);

  const tickers = portfolio?.positions.map((p) => p.ticker) ?? [];

  useEffect(() => {
    if (!portfolio) fetchPortfolio();
  }, [portfolio, fetchPortfolio]);

  useEffect(() => {
    if (tickers.length === 0 || fetched) return;
    setFetched(true);

    (async () => {
      for (const t of tickers) {
        if (!optionsWalls[t]) {
          try { await fetchOptionsWall(t); } catch { /* ignore */ }
        }
        if (!optionsWallSummaries[t]) fetchOptionsWallSummary(t);
      }
    })();
  }, [tickers.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefreshAll = () => {
    setFetched(false);
    (async () => {
      for (const t of tickers) {
        try { await fetchOptionsWall(t); } catch { /* ignore */ }
        fetchOptionsWallSummary(t);
      }
    })();
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
    return <div className="text-center text-gray-400 py-16">暂无持仓</div>;
  }

  const anyLoading = tickers.some((t) => loading[`wall_${t}`]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-700">
          期权墙分析（{tickers.length} 只）
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
        <OptionsWallCard
          key={ticker}
          ticker={ticker}
          wallData={optionsWalls[ticker]}
          summary={optionsWallSummaries[ticker]}
          isLoadingWall={!!loading[`wall_${ticker}`]}
          isLoadingSummary={!!loading[`wall_summary_${ticker}`]}
        />
      ))}
    </div>
  );
}
