import { OptionsChainView } from '../../modules/stock/OptionsChainView';
import { useStockStore } from '../../stores/stockStore';
import { useEffect } from 'react';

export function StockOptionsPage() {
  const portfolio = useStockStore((s) => s.portfolio);
  const fetchPortfolio = useStockStore((s) => s.fetchPortfolio);

  useEffect(() => {
    if (!portfolio) fetchPortfolio();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="max-w-5xl mx-auto py-8 px-6">
      <h1 className="text-lg font-semibold text-gray-800 mb-5">期权墙分析</h1>
      <OptionsChainView />
    </div>
  );
}
