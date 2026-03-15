import { useCallback, useEffect, useState } from 'react';
import { fetchJSON, putJSON, deleteJSON } from '../../api/client';
import {
  ArrowLeft, Brain, Plus, Trash2, Save, ChevronDown, ChevronUp,
  Check, X, Pencil, Layers, Thermometer, Server,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface LLMModel {
  id: number;
  name: string;
  provider: string;
  model: string;
  base_url: string;
  is_default: boolean;
  has_api_key: boolean;
  extra_params: string | null;
}

interface Assignment {
  id: number;
  scope: string;
  model_id: number;
  temperature: number | null;
}

interface ScopeInfo {
  scope: string;
  label: string;
  description: string;
}

const PROVIDER_PRESETS: Record<string, { base_url: string; models: string[] }> = {
  deepseek: { base_url: 'https://api.deepseek.com', models: ['deepseek-chat', 'deepseek-reasoner'] },
  openai: { base_url: '', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
  anthropic: { base_url: '', models: ['claude-sonnet-4-20250514', 'claude-3-5-haiku-20241022'] },
  google: { base_url: '', models: ['gemini-2.5-pro-preview-06-05', 'gemini-2.5-flash-preview-05-20', 'gemini-2.0-flash'] },
  qwen: { base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-plus', 'qwen-turbo', 'qwen-max'] },
};

const PROVIDERS = Object.keys(PROVIDER_PRESETS);

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`/api${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

/* ---------- Model Form ---------- */

function ModelForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: LLMModel;
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [provider, setProvider] = useState(initial?.provider ?? 'deepseek');
  const [model, setModel] = useState(initial?.model ?? '');
  const [name, setName] = useState(initial?.name ?? '');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(initial?.base_url ?? '');
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!initial) {
      const preset = PROVIDER_PRESETS[provider];
      if (preset) {
        setBaseUrl(preset.base_url);
        if (!model || !preset.models.includes(model)) {
          setModel(preset.models[0]);
        }
      }
    }
  }, [provider]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async () => {
    if (!name.trim() || !model.trim()) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        name: name.trim(),
        provider,
        model: model.trim(),
        base_url: baseUrl.trim() || null,
        is_default: isDefault,
      };
      if (apiKey) data.api_key = apiKey;
      await onSave(data);
    } finally {
      setSaving(false);
    }
  };

  const preset = PROVIDER_PRESETS[provider];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        {/* Provider */}
        <div className="flex flex-col gap-1">
          <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">Provider</label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
          >
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {/* Model */}
        <div className="flex flex-col gap-1">
          <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">Model</label>
          <div className="flex gap-2">
            <select
              value={preset?.models.includes(model) ? model : '__custom__'}
              onChange={(e) => {
                setModel(e.target.value === '__custom__' ? '' : e.target.value);
              }}
              className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
            >
              {preset?.models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
              <option value="__custom__">自定义...</option>
            </select>
            {(!preset || !preset.models.includes(model)) && (
              <input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="自定义模型名"
                className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
              />
            )}
          </div>
        </div>

        {/* Name */}
        <div className="flex flex-col gap-1">
          <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">名称</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例: DeepSeek-主力"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
          />
        </div>

        {/* API Key */}
        <div className="flex flex-col gap-1">
          <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">
            API Key {initial?.has_api_key && <span className="text-emerald-500">(已配置)</span>}
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={initial ? '留空不修改' : 'sk-...'}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
          />
        </div>

        {/* Base URL */}
        <div className="flex flex-col gap-1 col-span-2">
          <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">Base URL</label>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="留空使用默认"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 font-mono text-xs"
          />
        </div>
      </div>

      {/* Default toggle + actions */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="rounded border-gray-300"
          />
          设为全局默认
        </label>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving || !name.trim() || !model.trim()}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Main Page ---------- */

export function ModelManagementPage() {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [scopes, setScopes] = useState<ScopeInfo[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [showScopes, setShowScopes] = useState(true);

  const load = useCallback(async () => {
    const [m, a, s] = await Promise.all([
      fetchJSON<LLMModel[]>('/admin/llm/models'),
      fetchJSON<Assignment[]>('/admin/llm/assignments'),
      fetchJSON<ScopeInfo[]>('/admin/llm/scopes'),
    ]);
    setModels(m);
    setAssignments(a);
    setScopes(s);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (data: Record<string, unknown>) => {
    await postJSON('/admin/llm/models', data);
    setShowAdd(false);
    load();
  };

  const handleUpdate = async (id: number, data: Record<string, unknown>) => {
    await putJSON(`/admin/llm/models/${id}`, data);
    setEditId(null);
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此模型?')) return;
    await deleteJSON(`/admin/llm/models/${id}`);
    load();
  };

  const handleScopeAssign = async (scope: string, modelId: number, temperature: number | null) => {
    if (modelId === 0) {
      await deleteJSON(`/admin/llm/assignments/${scope}`);
    } else {
      await putJSON('/admin/llm/assignments', { scope, model_id: modelId, temperature });
    }
    load();
  };

  const getAssignment = (scope: string) => assignments.find((a) => a.scope === scope);

  return (
    <div className="min-h-screen bg-gray-50/70">
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link to="/admin" className="p-2 rounded-xl hover:bg-gray-100 transition-all duration-150 active:scale-95">
            <ArrowLeft className="w-5 h-5 text-gray-500" />
          </Link>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center shadow-sm">
            <Brain className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-800 leading-tight">模型管理</h1>
            <p className="text-xs text-gray-400">添加、配置和分配 LLM 模型</p>
          </div>
        </div>

        {/* ============ Models Section ============ */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-gray-500" />
            <h2 className="text-sm font-semibold text-gray-800">模型列表</h2>
            <span className="text-xs text-gray-400">{models.length} 个模型</span>
          </div>
          <button
            onClick={() => { setShowAdd(true); setEditId(null); }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            新增模型
          </button>
        </div>

        {showAdd && (
          <div className="mb-4">
            <ModelForm onSave={handleCreate} onCancel={() => setShowAdd(false)} />
          </div>
        )}

        <div className="space-y-3 mb-8">
          {models.map((m) => (
            <div key={m.id}>
              {editId === m.id ? (
                <ModelForm
                  initial={m}
                  onSave={(data) => handleUpdate(m.id, data)}
                  onCancel={() => setEditId(null)}
                />
              ) : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow duration-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-800">{m.name}</span>
                          {m.is_default && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-50 text-blue-600 rounded-md">
                              默认
                            </span>
                          )}
                          <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded-md ${
                            m.has_api_key ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'
                          }`}>
                            {m.has_api_key ? 'Key 已配置' : 'Key 未配置'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded font-mono">
                            {m.provider}
                          </span>
                          <span className="text-xs text-gray-500">{m.model}</span>
                          {m.base_url && (
                            <span className="text-[10px] text-gray-400 truncate max-w-[200px] font-mono">{m.base_url}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => { setEditId(m.id); setShowAdd(false); }}
                        className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                        title="编辑"
                      >
                        <Pencil className="w-3.5 h-3.5 text-gray-400" />
                      </button>
                      <button
                        onClick={() => handleDelete(m.id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-red-400" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
          {models.length === 0 && !showAdd && (
            <div className="text-center text-gray-400 text-sm py-8">暂无模型，点击"新增模型"添加</div>
          )}
        </div>

        {/* ============ Scope Assignments ============ */}
        <div className="mb-3">
          <button
            onClick={() => setShowScopes(!showScopes)}
            className="flex items-center gap-2 text-sm font-semibold text-gray-800 hover:text-blue-600 transition-colors"
          >
            <Layers className="w-4 h-4 text-gray-500" />
            模型分配
            {showScopes ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <p className="text-xs text-gray-400 mt-0.5 ml-6">为不同功能指定使用的模型，未指定则向上继承</p>
        </div>

        {showScopes && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50/80 text-gray-500 text-xs uppercase tracking-wider">
                  <th className="text-left px-4 py-3 font-semibold">功能</th>
                  <th className="text-left px-4 py-3 font-semibold">模型</th>
                  <th className="text-center px-4 py-3 font-semibold w-32">
                    <div className="flex items-center justify-center gap-1">
                      <Thermometer className="w-3 h-3" />
                      Temperature
                    </div>
                  </th>
                  <th className="text-center px-4 py-3 font-semibold w-16">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {scopes.map((s) => {
                  const assign = getAssignment(s.scope);
                  return (
                    <ScopeRow
                      key={s.scope}
                      scope={s}
                      assignment={assign}
                      models={models}
                      onSave={handleScopeAssign}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Scope Row ---------- */

function ScopeRow({
  scope,
  assignment,
  models,
  onSave,
}: {
  scope: ScopeInfo;
  assignment?: Assignment;
  models: LLMModel[];
  onSave: (scope: string, modelId: number, temperature: number | null) => Promise<void>;
}) {
  const [modelId, setModelId] = useState(assignment?.model_id ?? 0);
  const [temp, setTemp] = useState<string>(assignment?.temperature?.toString() ?? '');
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setModelId(assignment?.model_id ?? 0);
    setTemp(assignment?.temperature?.toString() ?? '');
    setDirty(false);
  }, [assignment]);

  const handleSave = async () => {
    await onSave(scope.scope, modelId, temp ? parseFloat(temp) : null);
    setDirty(false);
  };

  const indent = scope.scope.split('.').length - 1;

  return (
    <tr className="hover:bg-blue-50/30 transition-colors">
      <td className="px-4 py-3">
        <div style={{ paddingLeft: `${indent * 16}px` }}>
          <div className="text-sm font-medium text-gray-700">{scope.label}</div>
          <div className="text-[11px] text-gray-400 font-mono">{scope.scope}</div>
        </div>
      </td>
      <td className="px-4 py-3">
        <select
          value={modelId}
          onChange={(e) => { setModelId(Number(e.target.value)); setDirty(true); }}
          className="w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
        >
          <option value={0}>继承上级</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.provider}/{m.model})
            </option>
          ))}
        </select>
      </td>
      <td className="px-4 py-3 text-center">
        <input
          type="number"
          min="0"
          max="2"
          step="0.1"
          value={temp}
          onChange={(e) => { setTemp(e.target.value); setDirty(true); }}
          placeholder="—"
          className="w-20 mx-auto border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs text-center bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
        />
      </td>
      <td className="px-4 py-3 text-center">
        {dirty && (
          <button
            onClick={handleSave}
            className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors"
            title="保存"
          >
            <Check className="w-3.5 h-3.5 text-blue-600" />
          </button>
        )}
      </td>
    </tr>
  );
}
