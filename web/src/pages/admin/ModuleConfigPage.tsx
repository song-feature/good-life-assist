import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchJSON, putJSON } from '../../api/client';
import { ArrowLeft, Save, ToggleLeft, ToggleRight } from 'lucide-react';

interface ModuleInfo {
  module_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

const FIELD_LABELS: Record<string, string> = {
  futu_host: 'Futu Host',
  futu_port: 'Futu Port',
  market: '市场',
  env: '交易环境',
  prompt_options_wall: '期权墙分析 Prompt',
  prompt_recommendations: '投资建议 Prompt',
};

const SELECT_OPTIONS: Record<string, { label: string; value: string }[]> = {
  market: [
    { label: '美股 (US)', value: 'US' },
    { label: '港股 (HK)', value: 'HK' },
  ],
  env: [
    { label: '真实交易 (REAL)', value: 'REAL' },
    { label: '模拟交易 (SIMULATE)', value: 'SIMULATE' },
  ],
};

export function ModuleConfigPage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const [mod, setMod] = useState<ModuleInfo | null>(null);
  const [editConfig, setEditConfig] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!moduleId) return;
    fetchJSON<ModuleInfo[]>('/admin/modules').then((modules) => {
      const found = modules.find((m) => m.module_id === moduleId);
      if (found) {
        setMod(found);
        setEditConfig(found.config);
      }
    }).catch(console.error);
  }, [moduleId]);

  const toggleModule = useCallback(async () => {
    if (!mod) return;
    const next = !mod.enabled;
    await putJSON(`/admin/modules/${mod.module_id}/toggle?enabled=${next}`, {});
    setMod((prev) => prev ? { ...prev, enabled: next } : prev);
  }, [mod]);

  const saveConfig = useCallback(async () => {
    if (!mod) return;
    setSaving(true);
    try {
      await putJSON(`/admin/modules/${mod.module_id}/config`, editConfig);
      setMod((prev) => prev ? { ...prev, config: editConfig } : prev);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }, [mod, editConfig]);

  if (!mod) {
    return (
      <div className="min-h-screen bg-gray-50/70 flex items-center justify-center text-gray-400 text-sm">
        加载中...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50/70">
      <div className="max-w-3xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link to="/admin" className="p-2 rounded-xl hover:bg-gray-100 transition-all duration-150 active:scale-95">
            <ArrowLeft className="w-5 h-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-800 leading-tight">{mod.display_name}</h1>
            <p className="text-xs text-gray-400">{mod.description}</p>
          </div>
          <div className="ml-auto">
            <button onClick={toggleModule} className="flex items-center gap-1.5 transition-transform duration-150 hover:scale-105 active:scale-95">
              {mod.enabled ? <ToggleRight className="w-8 h-8 text-blue-600" /> : <ToggleLeft className="w-8 h-8 text-gray-300" />}
              <span className={`text-xs font-medium ${mod.enabled ? 'text-blue-600' : 'text-gray-400'}`}>
                {mod.enabled ? '已启用' : '已禁用'}
              </span>
            </button>
          </div>
        </div>

        {/* Config form */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-sm font-semibold text-gray-800 mb-4">模块配置</h2>
          <div className="space-y-4">
            {Object.entries(editConfig).map(([key, val]) => {
              const isPrompt = key.startsWith('prompt_');
              const isSelect = key in SELECT_OPTIONS;
              const label = FIELD_LABELS[key] || key;

              return (
                <div key={key} className={isPrompt ? '' : 'flex items-center gap-3'}>
                  <label className={`text-xs shrink-0 ${isPrompt ? 'block mb-1.5 font-medium text-gray-600' : 'w-32 text-gray-500 font-mono'}`}>
                    {label}
                  </label>
                  {isPrompt ? (
                    <textarea
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all min-h-[120px] resize-y font-mono leading-relaxed"
                      value={String(val ?? '')}
                      onChange={(e) => setEditConfig((prev) => ({ ...prev, [key]: e.target.value }))}
                    />
                  ) : isSelect ? (
                    <select
                      className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                      value={String(val ?? '')}
                      onChange={(e) => setEditConfig((prev) => ({ ...prev, [key]: e.target.value }))}
                    >
                      {SELECT_OPTIONS[key].map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                      value={String(val ?? '')}
                      onChange={(e) => setEditConfig((prev) => ({ ...prev, [key]: e.target.value }))}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 mt-6 pt-4 border-t border-gray-100">
            <button
              onClick={saveConfig}
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              <Save className="w-4 h-4" />
              {saving ? '保存中...' : '保存配置'}
            </button>
            {saved && <span className="text-xs text-emerald-600 font-medium">已保存</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
