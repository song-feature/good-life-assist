import { create } from 'zustand';

interface ModuleState {
  activeModule: string | null;
  activeAction: string | null;
  moduleData: Record<string, unknown>;
  handleUICommand: (cmd: { module: string; action: string; data: Record<string, unknown> }) => void;
  clearModule: () => void;
}

export const useModuleStore = create<ModuleState>((set) => ({
  activeModule: null,
  activeAction: null,
  moduleData: {},

  handleUICommand: (cmd) => {
    set({
      activeModule: cmd.module,
      activeAction: cmd.action,
      moduleData: cmd.data,
    });
  },

  clearModule: () => {
    set({ activeModule: null, activeAction: null, moduleData: {} });
  },
}));
