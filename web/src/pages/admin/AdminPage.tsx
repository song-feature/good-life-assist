import { useCallback, useEffect, useState } from 'react';
import { fetchJSON, putJSON, deleteJSON } from '../../api/client';
import {
  Settings, ToggleLeft, ToggleRight, Brain,
  ScrollText, RefreshCw, Trash2, Search, ChevronRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface ModuleInfo {
  module_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

interface LLMConfig {
  provider: string;
  model: string;
  base_url: string;
  has_api_key: boolean;
}

interface LogEntry {
  timestamp: string;
  level: string;
  logger_name: string;
  message: string;
}

type Tab = 'settings' | 'logs';

const LEVEL_OPTIONS = ['', 'WARNING', 'ERROR', 'CRITICAL'] as const;

const levelColor: Record<string, string> = {
  WARNING: 'bg-yellow-100 text-yellow-800',
  ERROR: 'bg-red-100 text-red-700',
  CRITICAL: 'bg-red-200 text-red-900 font-bold',
};

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('settings');

  // ---- settings state ----
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [llmConfig, setLLMConfig] = useState<LLMConfig | null>(null);

  // ---- logs state ----
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logTotal, setLogTotal] = useState(0);
  const [logLevel, setLogLevel] = useState('');
  const [logLogger, setLogLogger] = useState('');
  const [logKeyword, setLogKeyword] = useState('');
  const [logLimit, setLogLimit] = useState(200);
  const [logsLoading, setLogsLoading] = useState(false);

  // ---- load settings ----
  useEffect(() => {
    fetchJSON<ModuleInfo[]>('/admin/modules').then(setModules).catch(console.error);
    fetchJSON<LLMConfig>('/admin/llm/config').then(setLLMConfig).catch(console.error);
  }, []);

  // ---- load logs ----
  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const params = new URLSearchParams();
      if (logLevel) params.set('level', logLevel);
      if (logLogger) params.set('logger', logLogger);
      if (logKeyword) params.set('keyword', logKeyword);
      params.set('limit', String(logLimit));
      const qs = params.toString();
      const res = await fetchJSON<{ total: number; logs: LogEntry[] }>(`/admin/logs?${qs}`);
      setLogs(res.logs);
      setLogTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLogsLoading(false);
    }
  }, [logLevel, logLogger, logKeyword, logLimit]);

  useEffect(() => {
    if (tab === 'logs') fetchLogs();
  }, [tab, fetchLogs]);

  const clearLogs = async () => {
    if (!confirm('确定清空所有日志?')) return;
    await deleteJSON('/admin/logs');
    setLogs([]);
    setLogTotal(0);
  };

  // ---- module helpers ----
  const toggleModule = async (moduleId: string, enabled: boolean) => {
    await putJSON(`/admin/modules/${moduleId}/toggle?enabled=${enabled}`, {});
    setModules((prev) =>
      prev.map((m) => (m.module_id === moduleId ? { ...m, enabled } : m)),
    );
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-6">
      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-gray-200 mb-6">
          <button
            onClick={() => setTab('settings')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-all duration-150 ${
              tab === 'settings'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            <Settings className="w-4 h-4" />
            设置
          </button>
          <button
            onClick={() => setTab('logs')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-all duration-150 ${
              tab === 'logs'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            <ScrollText className="w-4 h-4" />
            日志
            {logTotal > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs font-semibold rounded-full bg-red-50 text-red-600">
                {logTotal}
              </span>
            )}
          </button>
        </div>

        {/* ============ Settings Tab ============ */}
        {tab === 'settings' && (
          <>
            {/* LLM Config - Link to Model Management */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
                    <Brain className="w-4.5 h-4.5 text-purple-600" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-gray-800">LLM 模型管理</h2>
                    <p className="text-xs text-gray-400 mt-0.5">配置多个模型，按功能分配</p>
                  </div>
                </div>
                <Link
                  to="/admin/models"
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                >
                  管理模型 <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              {llmConfig && (
                <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-3 gap-3 text-xs text-gray-500">
                  <div>
                    <span className="text-gray-400">当前模型: </span>
                    <span className="font-medium text-gray-700">{llmConfig.provider}/{llmConfig.model}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">来源: </span>
                    <span className="font-medium text-gray-700">{(llmConfig as Record<string, unknown>).source as string || 'env'}</span>
                  </div>
                  <div>
                    <span className={`inline-flex items-center gap-1 font-medium ${llmConfig.has_api_key ? 'text-emerald-600' : 'text-red-500'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${llmConfig.has_api_key ? 'bg-emerald-500' : 'bg-red-400'}`} />
                      {llmConfig.has_api_key ? 'Key 已配置' : 'Key 未配置'}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Module List */}
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-sm font-semibold text-gray-800">模块管理</h2>
              <span className="text-xs text-gray-400">{modules.length} 个模块</span>
            </div>
            <div className="space-y-3">
              {modules.map((mod) => (
                <div
                  key={mod.module_id}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-800 text-sm">{mod.display_name}</span>
                      <span className="text-[11px] text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded-md font-mono">
                        {mod.module_id}
                      </span>
                    </div>
                    <button
                      onClick={() => toggleModule(mod.module_id, !mod.enabled)}
                      className="flex items-center gap-1.5 transition-transform duration-150 hover:scale-105 active:scale-95"
                    >
                      {mod.enabled ? (
                        <ToggleRight className="w-8 h-8 text-blue-600" />
                      ) : (
                        <ToggleLeft className="w-8 h-8 text-gray-300" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mb-3 leading-relaxed">{mod.description}</p>

                  <Link
                    to={`/admin/modules/${mod.module_id}`}
                    className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
                  >
                    编辑配置 <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ============ Logs Tab ============ */}
        {tab === 'logs' && (
          <>
            {/* Toolbar */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4">
              <div className="flex flex-wrap items-end gap-3">
                {/* Level filter */}
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">级别</label>
                  <select
                    value={logLevel}
                    onChange={(e) => setLogLevel(e.target.value)}
                    className="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                  >
                    {LEVEL_OPTIONS.map((l) => (
                      <option key={l} value={l}>{l || '全部'}</option>
                    ))}
                  </select>
                </div>

                {/* Logger filter */}
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">Logger</label>
                  <input
                    placeholder="logger 名称"
                    value={logLogger}
                    onChange={(e) => setLogLogger(e.target.value)}
                    className="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm w-40 bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                  />
                </div>

                {/* Keyword filter */}
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">关键词</label>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                    <input
                      placeholder="搜索内容"
                      value={logKeyword}
                      onChange={(e) => setLogKeyword(e.target.value)}
                      className="border border-gray-200 rounded-lg pl-8 pr-2.5 py-1.5 text-sm w-44 bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                    />
                  </div>
                </div>

                {/* Limit */}
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-gray-400 uppercase tracking-wide font-medium">条数</label>
                  <select
                    value={logLimit}
                    onChange={(e) => setLogLimit(Number(e.target.value))}
                    className="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                  >
                    {[50, 100, 200, 500].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>

                {/* Actions */}
                <div className="flex gap-2 ml-auto">
                  <button
                    onClick={fetchLogs}
                    disabled={logsLoading}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${logsLoading ? 'animate-spin' : ''}`} />
                    刷新
                  </button>
                  <button
                    onClick={clearLogs}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    清空
                  </button>
                </div>
              </div>
            </div>

            {/* Log entries */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              {logs.length === 0 ? (
                <div className="py-20 text-center text-gray-400 text-sm">
                  <ScrollText className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p>暂无日志</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
                  {logs.map((entry, idx) => (
                    <div
                      key={idx}
                      className={`px-4 py-3 hover:bg-blue-50/30 text-sm transition-colors ${
                        idx % 2 === 0 ? '' : 'bg-gray-50/30'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[11px] text-gray-400 font-mono whitespace-nowrap tabular-nums">
                          {entry.timestamp}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 text-[11px] rounded-md font-medium ${
                            levelColor[entry.level] ?? 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {entry.level}
                        </span>
                        <span className="text-[11px] text-gray-400 truncate max-w-[200px] font-mono">
                          {entry.logger_name}
                        </span>
                      </div>
                      <p className="text-gray-700 whitespace-pre-wrap break-all leading-relaxed text-[13px]">
                        {entry.message}
                      </p>
                    </div>
                  ))}
                </div>
              )}
              {logs.length > 0 && (
                <div className="border-t border-gray-100 px-4 py-2.5 text-xs text-gray-400 text-right font-medium">
                  共 {logTotal} 条日志
                </div>
              )}
            </div>
          </>
        )}
    </div>
  );
}
