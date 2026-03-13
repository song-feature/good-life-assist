import { useStockStore } from '../../stores/stockStore';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

function SignalBadge({ signal }: { signal: string }) {
  const config: Record<string, { label: string; color: string }> = {
    golden_cross: { label: '金叉', color: 'bg-green-100 text-green-700' },
    death_cross: { label: '死叉', color: 'bg-red-100 text-red-700' },
    neutral: { label: '中性', color: 'bg-gray-100 text-gray-700' },
    bullish: { label: '看涨', color: 'bg-green-100 text-green-700' },
    bearish: { label: '看跌', color: 'bg-red-100 text-red-700' },
  };
  const c = config[signal] || { label: signal, color: 'bg-gray-100 text-gray-600' };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${c.color}`}>
      {c.label}
    </span>
  );
}

function RSIGauge({ value }: { value: number | null }) {
  if (value == null) return <span className="text-xs text-gray-400">—</span>;
  const color = value > 70 ? 'text-red-600' : value < 30 ? 'text-green-600' : 'text-gray-700';
  const label = value > 70 ? '超买' : value < 30 ? '超卖' : '中性';
  return (
    <div className="flex items-center gap-1">
      <span className={`text-sm font-semibold ${color}`}>{value}</span>
      <span className={`text-xs ${color}`}>{label}</span>
    </div>
  );
}

export function AnalysisView() {
  const analysis = useStockStore((s) => s.analysis);
  const loading = useStockStore((s) => s.loading.analysis);
  const fetchAnalysis = useStockStore((s) => s.fetchAnalysis);

  if (!analysis && !loading) {
    return (
      <div className="text-center text-gray-400 py-16">
        <p>等待 Agent 生成分析报告...</p>
        <p className="text-xs mt-1 mb-4">试试说"给我分析一下持仓"</p>
        <button
          onClick={fetchAnalysis}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          手动加载
        </button>
      </div>
    );
  }

  if (loading) {
    return <div className="text-center text-gray-400 py-16">加载中...（分析数据较多，请耐心等待）</div>;
  }

  const holdings = (analysis.holdings || []) as Record<string, unknown>[];

  return (
    <div>
      <div className="space-y-3 mb-4">
        {holdings.map((h) => {
          const plVal = (h.pl_val as number) || 0;
          const plRatio = (h.pl_ratio as number) || 0;
          const plColor = plVal >= 0 ? 'text-green-600' : 'text-red-600';

          return (
            <div key={h.ticker as string} className="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-base font-semibold text-gray-800">{h.ticker as string}</span>
                  <span className="text-sm text-gray-500">{h.name as string}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm">{h.qty as number} 股</span>
                  <span className={`text-sm font-medium ${plColor}`}>
                    {plVal >= 0 ? '+' : ''}${plVal.toFixed(2)} ({plRatio >= 0 ? '+' : ''}{plRatio.toFixed(2)}%)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-xs text-gray-500">MA 信号</span>
                  <div className="mt-0.5">
                    <SignalBadge signal={h.ma_signal as string} />
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">RSI(14)</span>
                  <div className="mt-0.5">
                    <RSIGauge value={h.rsi14 as number | null} />
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">5日涨跌</span>
                  <div className="mt-0.5">
                    {h.price_change_5d_pct != null ? (
                      <span className={`text-sm font-medium ${
                        (h.price_change_5d_pct as number) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {(h.price_change_5d_pct as number) >= 0 ? '+' : ''}{(h.price_change_5d_pct as number).toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">期权情绪</span>
                  <div className="mt-0.5">
                    <SignalBadge signal={h.options_sentiment as string} />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
        <p className="text-xs text-amber-700">
          以上分析基于技术指标和期权数据，仅供参考。请结合基本面和市场环境综合判断。
        </p>
      </div>
    </div>
  );
}
