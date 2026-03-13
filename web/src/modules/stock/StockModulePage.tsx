import { useEffect, useRef, useState } from 'react';
import { useModuleStore } from '../../stores/moduleStore';
import { PortfolioView } from './PortfolioView';
import { StockChart } from './StockChart';
import { OptionsChainView } from './OptionsChainView';
import { BarChart3, TrendingUp, GitBranch } from 'lucide-react';

const TABS = [
  { id: 'show_portfolio', label: '持仓总览', icon: BarChart3 },
  { id: 'show_trend', label: '走势图', icon: TrendingUp },
  { id: 'show_options', label: '期权链', icon: GitBranch },
] as const;

type TabId = (typeof TABS)[number]['id'];

// Map agent actions to tab ids (show_analysis merged into show_portfolio)
function resolveTab(action: string | null): TabId {
  if (action === 'show_analysis') return 'show_portfolio';
  if (TABS.some((t) => t.id === action)) return action as TabId;
  return 'show_portfolio';
}

export function StockModulePage() {
  const activeAction = useModuleStore((s) => s.activeAction);
  const [currentTab, setCurrentTab] = useState<TabId>(resolveTab(activeAction));
  const prevAction = useRef(activeAction);

  // Only sync when activeAction is changed by agent (not on every render)
  useEffect(() => {
    if (activeAction && activeAction !== prevAction.current) {
      setCurrentTab(resolveTab(activeAction));
    }
    prevAction.current = activeAction;
  }, [activeAction]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-1 px-5 pt-3 pb-0 border-b border-gray-100 bg-white">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const active = currentTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setCurrentTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-all duration-150 ${
                active
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-400 hover:text-gray-600'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>
      <div className="flex-1 overflow-auto p-5 bg-gray-50/70">
        {currentTab === 'show_portfolio' && <PortfolioView />}
        {currentTab === 'show_trend' && <StockChart />}
        {currentTab === 'show_options' && <OptionsChainView />}
      </div>
    </div>
  );
}
