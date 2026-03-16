import { PortfolioView } from '../../modules/stock/PortfolioView';
import { useStockStore } from '../../stores/stockStore';
import { useEffect } from 'react';

export function StockPortfolioPage() {
  const portfolio = useStockStore((s) => s.portfolio);
  const fetchPortfolio = useStockStore((s) => s.fetchPortfolio);

  useEffect(() => {
    if (!portfolio) fetchPortfolio();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="max-w-5xl mx-auto py-8 px-6">
      <h1 className="text-lg font-semibold text-gray-800 mb-5">持仓总览</h1>
      <PortfolioView />
    </div>
  );
}
