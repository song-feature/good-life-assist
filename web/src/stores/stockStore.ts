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
  prev_close?: number;
  price_change?: number;
  price_change_pct?: number;
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

/* --- Options Wall types --- */

export interface WallEntry {
  strike: number;
  openInterest: number;
  volume: number;
}

export interface WallAnalysis {
  expiry_date: string;
  underlying_price: number;
  call_walls: WallEntry[];
  put_walls: WallEntry[];
  max_pain: number | null;
  total_calls_oi: number;
  total_puts_oi: number;
  put_call_ratio: number;
}

export interface OptionsWallData {
  ticker: string;
  current_price: number | null;
  this_friday: WallAnalysis | null;
  next_friday: WallAnalysis | null;
}

/* --- Store --- */

interface StockState {
  portfolio: { positions: Position[]; funds: Funds | null; today_pl_total: number } | null;
  trends: Record<string, TrendData>;
  optionsChain: OptionsData | null;
  optionsChains: Record<string, OptionsData>;
  analysis: AnalysisReport | null;
  optionsWalls: Record<string, OptionsWallData>;
  optionsWallSummaries: Record<string, string>;
  analysisRecommendations: string | null;
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
  fetchOptionsWall: (ticker: string) => Promise<void>;
  fetchOptionsWallSummary: (ticker: string) => Promise<void>;
  fetchAnalysisRecommendations: () => Promise<void>;
}

export const useStockStore = create<StockState>((set) => ({
  portfolio: null,
  trends: {},
  optionsChain: null,
  optionsChains: {},
  analysis: null,
  optionsWalls: {},
  optionsWallSummaries: {},
  analysisRecommendations: null,
  loading: {},

  setPortfolio: (data) => set({ portfolio: data }),
  setTrend: (ticker, data) => set((s) => ({ trends: { ...s.trends, [ticker]: data } })),
  setOptionsChain: (data) => set({ optionsChain: data }),
  setAnalysis: (data) => set({ analysis: data }),

  fetchPortfolio: async () => {
    const prev = useStockStore.getState().portfolio;
    if (!prev) {
      set((s) => ({ loading: { ...s.loading, portfolio: true } }));
    }
    try {
      const data = await fetchJSON<{ positions: Position[]; funds: Funds | null; today_pl_total: number }>(
        '/modules/stock/portfolio',
      );
      if (data && data.positions && data.positions.length > 0) {
        set({ portfolio: data });
      } else if (!prev) {
        set({ portfolio: data });
      }
    } finally {
      set((s) => ({ loading: { ...s.loading, portfolio: false } }));
    }
  },

  fetchTrend: async (ticker, period = '1mo') => {
    const key = `${ticker}:${period}`;
    set((s) => ({ loading: { ...s.loading, [`trend_${key}`]: true } }));
    try {
      const data = await fetchJSON<TrendData>(`/modules/stock/trend/${ticker}?period=${period}`);
      set((s) => ({ trends: { ...s.trends, [key]: data } }));
    } finally {
      set((s) => ({ loading: { ...s.loading, [`trend_${key}`]: false } }));
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

  fetchOptionsWall: async (ticker) => {
    set((s) => ({ loading: { ...s.loading, [`wall_${ticker}`]: true } }));
    try {
      const data = await fetchJSON<OptionsWallData>(`/modules/stock/options/${ticker}/wall`);
      if (data && data.ticker) {
        set((s) => ({ optionsWalls: { ...s.optionsWalls, [ticker]: data } }));
      }
    } finally {
      set((s) => ({ loading: { ...s.loading, [`wall_${ticker}`]: false } }));
    }
  },

  fetchOptionsWallSummary: async (ticker) => {
    set((s) => ({ loading: { ...s.loading, [`wall_summary_${ticker}`]: true } }));
    try {
      const data = await fetchJSON<{ ticker: string; summary: string }>(
        `/modules/stock/options/${ticker}/wall-summary`,
      );
      if (data && data.summary) {
        set((s) => ({ optionsWallSummaries: { ...s.optionsWallSummaries, [ticker]: data.summary } }));
      }
    } finally {
      set((s) => ({ loading: { ...s.loading, [`wall_summary_${ticker}`]: false } }));
    }
  },

  fetchAnalysisRecommendations: async () => {
    set((s) => ({ loading: { ...s.loading, analysis_recommendations: true } }));
    try {
      const data = await fetchJSON<{ recommendations: string }>('/modules/stock/analysis/recommendations');
      if (data && data.recommendations) {
        set({ analysisRecommendations: data.recommendations });
      }
    } finally {
      set((s) => ({ loading: { ...s.loading, analysis_recommendations: false } }));
    }
  },
}));
