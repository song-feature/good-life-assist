import { create } from 'zustand';
import { fetchJSON } from '../api/client';

export interface Position {
  ticker: string;
  name: string;
  qty: number;
  cost_price: number;
  current_price: number;
  market_val: number;
  pl_val: number;
  pl_ratio: number;
  today_pl_val: number;
  session?: string;
  ma5?: number | null;
  ma20?: number | null;
  rsi14?: number | null;
  ma_signal?: string;
  price_change_5d_pct?: number | null;
  options_sentiment?: string;
}

export interface Funds {
  total_assets: number;
  market_val: number;
  cash: number;
  local_cash: number;
  unrealized_pl: number;
  realized_pl: number;
}

export interface TrendData {
  ticker: string;
  closes: number[];
  dates?: string[];
  ma5: (number | null)[];
  ma20: (number | null)[];
  rsi14: number | null;
  current_price: number | null;
  price_change_5d_pct: number | null;
  ma_signal?: string;
}

export interface OptionsData {
  code: string;
  expiry_date: string;
  underlying_price: number;
  calls: Record<string, unknown>[];
  puts: Record<string, unknown>[];
}

export interface AnalysisReport {
  holdings: Record<string, unknown>[];
  funds: Funds | null;
  today_pl_total: number;
  recommendations?: string;
}

interface StockState {
  portfolio: { positions: Position[]; funds: Funds | null; today_pl_total: number } | null;
  trends: Record<string, TrendData>;
  optionsChain: OptionsData | null;
  optionsChains: Record<string, OptionsData>;
  analysis: AnalysisReport | null;
  loading: Record<string, boolean>;

  setPortfolio: (data: { positions: Position[]; funds: Funds | null; today_pl_total: number }) => void;
  setTrend: (ticker: string, data: TrendData) => void;
  setOptionsChain: (data: OptionsData | null) => void;
  setAnalysis: (data: AnalysisReport | null) => void;

  fetchPortfolio: () => Promise<void>;
  fetchTrend: (ticker: string, period?: string) => Promise<void>;
  fetchOptionsChain: (ticker: string, expiry?: string) => Promise<void>;
  fetchOptionsForTicker: (ticker: string, expiry?: string) => Promise<void>;
  fetchAnalysis: () => Promise<void>;
}

export const useStockStore = create<StockState>((set) => ({
  portfolio: null,
  trends: {},
  optionsChain: null,
  optionsChains: {},
  analysis: null,
  loading: {},

  setPortfolio: (data) => set({ portfolio: data }),
  setTrend: (ticker, data) => set((s) => ({ trends: { ...s.trends, [ticker]: data } })),
  setOptionsChain: (data) => set({ optionsChain: data }),
  setAnalysis: (data) => set({ analysis: data }),

  fetchPortfolio: async () => {
    const prev = useStockStore.getState().portfolio;
    // Only show loading spinner when there's no existing data
    if (!prev) {
      set((s) => ({ loading: { ...s.loading, portfolio: true } }));
    }
    try {
      const data = await fetchJSON<{ positions: Position[]; funds: Funds | null; today_pl_total: number }>(
        '/modules/stock/portfolio',
      );
      // Only update if we got valid data; never overwrite good data with empty
      if (data && data.positions && data.positions.length > 0) {
        set({ portfolio: data });
      } else if (!prev) {
        // First load: store whatever came back
        set({ portfolio: data });
      }
    } finally {
      set((s) => ({ loading: { ...s.loading, portfolio: false } }));
    }
  },

  fetchTrend: async (ticker, period = '1mo') => {
    set((s) => ({ loading: { ...s.loading, [`trend_${ticker}`]: true } }));
    try {
      const data = await fetchJSON<TrendData>(`/modules/stock/trend/${ticker}?period=${period}`);
      set((s) => ({ trends: { ...s.trends, [ticker]: data } }));
    } finally {
      set((s) => ({ loading: { ...s.loading, [`trend_${ticker}`]: false } }));
    }
  },

  fetchOptionsChain: async (ticker, expiry) => {
    set((s) => ({ loading: { ...s.loading, options: true } }));
    try {
      const url = expiry
        ? `/modules/stock/options/${ticker}?expiry=${expiry}`
        : `/modules/stock/options/${ticker}`;
      const data = await fetchJSON<OptionsData>(url);
      set({ optionsChain: data });
    } finally {
      set((s) => ({ loading: { ...s.loading, options: false } }));
    }
  },

  fetchOptionsForTicker: async (ticker, expiry) => {
    set((s) => ({ loading: { ...s.loading, [`options_${ticker}`]: true } }));
    try {
      const url = expiry
        ? `/modules/stock/options/${ticker}?expiry=${expiry}`
        : `/modules/stock/options/${ticker}`;
      const data = await fetchJSON<OptionsData>(url);
      if (data && !('error' in data)) {
        set((s) => ({ optionsChains: { ...s.optionsChains, [ticker]: data } }));
      }
    } finally {
      set((s) => ({ loading: { ...s.loading, [`options_${ticker}`]: false } }));
    }
  },

  fetchAnalysis: async () => {
    set((s) => ({ loading: { ...s.loading, analysis: true } }));
    try {
      const data = await fetchJSON<AnalysisReport>('/modules/stock/analysis');
      set({ analysis: data });
    } finally {
      set((s) => ({ loading: { ...s.loading, analysis: false } }));
    }
  },
}));
