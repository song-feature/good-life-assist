import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchJSON, putJSON, postJSON } from '../../api/client';
import { ArrowLeft, Save, FlaskConical, Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'password' | 'number' | 'select';
  required?: boolean;
  description?: string;
  options?: { label: string; value: string }[];
}

interface ChannelConfigData {
  channel_id: string;
  display_name: string;
  description: string;
  channel_type: string;
  config_schema: ConfigField[];
  config: Record<string, string>;
  enabled: boolean;
  status: string;
  status_message: string;
}

interface TestResult {
  success: boolean;
  message: string;
}

export function ChannelConfigPage() {
  const { channelId } = useParams<{ channelId: string }>();
  const [data, setData] = useState<ChannelConfigData | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    if (!channelId) return;
    fetchJSON<ChannelConfigData>(`/admin/channels/${channelId}/config`)
      .then((d) => {
        setData(d);
        setFormValues(d.config || {});
      })
      .catch(console.error);
  }, [channelId]);

  const handleChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (!channelId) return;
    setSaving(true);
    setSaveMsg('');
    try {
      await putJSON(`/admin/channels/${channelId}/config`, { config: formValues });
      setSaveMsg('配置已保存');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e) {
      setSaveMsg('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!channelId) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await postJSON<TestResult>(`/admin/channels/${channelId}/test`, { config: formValues });
      setTestResult(result);
    } catch (e) {
      setTestResult({ success: false, message: '请求失败' });
    } finally {
      setTesting(false);
    }
  };

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto py-8 px-6 flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/admin/channels"
          className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-blue-600 transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          返回通道列表
        </Link>
        <h1 className="text-sm font-bold text-gray-800">{data.display_name} 配置</h1>
        <p className="text-xs text-gray-400 mt-1">{data.description}</p>
      </div>

      {/* Config Form */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-5">
        {data.config_schema.map((field) => (
          <div key={field.key}>
            <label className="block text-[13px] font-medium text-gray-700 mb-1.5">
              {field.label}
              {field.required && <span className="text-red-400 ml-0.5">*</span>}
            </label>
            {field.description && (
              <p className="text-[11px] text-gray-400 mb-1.5">{field.description}</p>
            )}
            {field.type === 'select' ? (
              <select
                value={formValues[field.key] || ''}
                onChange={(e) => handleChange(field.key, e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
              >
                <option value="">请选择</option>
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
                value={formValues[field.key] || ''}
                onChange={(e) => handleChange(field.key, e.target.value)}
                placeholder={field.type === 'password' && formValues[field.key] === '••••••••' ? '已配置，留空保持不变' : ''}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
              />
            )}
          </div>
        ))}

        {/* Test Result */}
        {testResult && (
          <div
            className={`flex items-start gap-2 rounded-lg px-4 py-3 text-sm ${
              testResult.success ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
            )}
            <span>{testResult.message}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            保存配置
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FlaskConical className="w-3.5 h-3.5" />}
            测试连接
          </button>
          {saveMsg && (
            <span className={`text-xs font-medium ${saveMsg === '配置已保存' ? 'text-emerald-600' : 'text-red-500'}`}>
              {saveMsg}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
