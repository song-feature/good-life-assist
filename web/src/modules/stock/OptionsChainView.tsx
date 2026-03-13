import { useEffect, useState } from 'react';
import { useStockStore, type OptionsData } from '../../stores/stockStore';
import { Loader2, RefreshCw } from 'lucide-react';

function OptionTable({ options }: { options: Record<string, unknown>[] }) {
  if (!options.length) {
    return <div className="text-center text-gray-400 py-4 text-sm">暂无数据</div>;
  }

  return (
    <div className="overflow-auto max-h-[400px]">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-gray-50">
          <tr className="text-gray-500">
            <th className="text-right px-2 py-2">行权价</th>
            <th className="text-right px-2 py-2">最新价</th>
            <th className="text-right px-2 py-2">买价</th>
            <th className="text-right px-2 py-2">卖价</th>
            <th className="text-right px-2 py-2">成交量</th>
            <th className="text-right px-2 py-2">未平仓</th>
            <th className="text-right px-2 py-2">IV</th>
            <th className="text-center px-2 py-2">ITM</th>
          </tr>
        </thead>
        <tbody>
          {options.map((opt, i) => {
            const itm = opt.inTheMoney as boolean;
            return (
              <tr
                key={i}
                className={`border-t border-gray-50 ${itm ? 'bg-blue-50/50' : ''} hover:bg-gray-50`}
              >
                <td className="text-right px-2 py-1.5 font-medium">${(opt.strike as number)?.toFixed(2)}</td>
                <td className="text-right px-2 py-1.5">${(opt.lastPrice as number)?.toFixed(2)}</td>
                <td className="text-right px-2 py-1.5">${(opt.bid as number)?.toFixed(2)}</td>
                <td className="text-right px-2 py-1.5">${(opt.ask as number)?.toFixed(2)}</td>
                <td className="text-right px-2 py-1.5">{(opt.volume as number)?.toLocaleString()}</td>
                <td className="text-right px-2 py-1.5">{(opt.openInterest as number)?.toLocaleString()}</td>
                <td className="text-right px-2 py-1.5">{((opt.impliedVolatility as number) * 100)?.toFixed(1)}%</td>
                <td className="text-center px-2 py-1.5">
                  {itm && <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TickerOptionsCard({ ticker, data, isLoading }: {
  ticker: string;
  data: OptionsData | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-6 mb-4">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">{ticker} 期权数据加载中...</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4 mb-4">
        <span className="text-sm font-semibold text-gray-800">{ticker}</span>
        <span className="text-sm text-gray-400 ml-2">暂无期权数据</span>
      </div>
    );
  }

  const calls = (data.calls || []) as Record<string, unknown>[];
  const puts = (data.puts || []) as Record<string, unknown>[];
  const callsOI = calls.reduce((s, c) => s + ((c.openInterest as number) || 0), 0);
  const putsOI = puts.reduce((s, p) => s + ((p.openInterest as number) || 0), 0);
  const pcRatio = callsOI > 0 ? (putsOI / callsOI).toFixed(2) : '—';

  return (
    <div className="mb-5">
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-3 mb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-gray-800">{data.code}</h3>
            <span className="text-xs text-gray-500">到期日: {data.expiry_date}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-600">
            <span>标的价: <b>${data.underlying_price?.toFixed(2)}</b></span>
            <span>P/C: <b className={Number(pcRatio) > 1 ? 'text-red-600' : Number(pcRatio) < 0.7 ? 'text-green-600' : ''}>{pcRatio}</b></span>
            <span>Call OI: <b>{callsOI.toLocaleString()}</b></span>
            <span>Put OI: <b>{putsOI.toLocaleString()}</b></span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-3 py-1.5 bg-green-50 text-green-700 font-medium text-xs">
            Calls (看涨)
          </div>
          <OptionTable options={calls} />
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-3 py-1.5 bg-red-50 text-red-700 font-medium text-xs">
            Puts (看跌)
          </div>
          <OptionTable options={puts} />
        </div>
      </div>
    </div>
  );
}

export function OptionsChainView() {
  const portfolio = useStockStore((s) => s.portfolio);
  const optionsChains = useStockStore((s) => s.optionsChains);
  const loading = useStockStore((s) => s.loading);
  const fetchOptionsForTicker = useStockStore((s) => s.fetchOptionsForTicker);
  const fetchPortfolio = useStockStore((s) => s.fetchPortfolio);
  const [fetched, setFetched] = useState(false);

  const tickers = portfolio?.positions.map((p) => p.ticker) ?? [];

  // Auto-fetch portfolio if not yet loaded
  useEffect(() => {
    if (!portfolio) fetchPortfolio();
  }, [portfolio, fetchPortfolio]);

  // Auto-fetch options for all holdings when portfolio is available
  useEffect(() => {
    if (tickers.length === 0 || fetched) return;
    setFetched(true);
    tickers.forEach((t) => {
      if (!optionsChains[t]) {
        fetchOptionsForTicker(t);
      }
    });
  }, [tickers.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefreshAll = () => {
    setFetched(false);
    tickers.forEach((t) => fetchOptionsForTicker(t));
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

  const anyLoading = tickers.some((t) => loading[`options_${t}`]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-700">
          持仓期权链（{tickers.length} 只）
        </h2>
        <button
          onClick={handleRefreshAll}
          disabled={anyLoading}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${anyLoading ? 'animate-spin' : ''}`} />
          刷新全部
        </button>
      </div>

      {tickers.map((ticker) => (
        <TickerOptionsCard
          key={ticker}
          ticker={ticker}
          data={optionsChains[ticker]}
          isLoading={!!loading[`options_${ticker}`]}
        />
      ))}
    </div>
  );
}
