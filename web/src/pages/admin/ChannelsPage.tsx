import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchJSON, putJSON } from '../../api/client';
import { Radio, ChevronRight, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react';

interface ChannelInfo {
  channel_id: string;
  channel_type: string;
  display_name: string;
  description: string;
  enabled: boolean;
  status: string;
  status_message: string;
  is_running: boolean;
}

const STATUS_MAP: Record<string, { label: string; color: string; dot: string }> = {
  running: { label: '运行中', color: 'text-emerald-600', dot: 'bg-emerald-500' },
  stopped: { label: '已停止', color: 'text-gray-400', dot: 'bg-gray-300' },
  error: { label: '异常', color: 'text-red-500', dot: 'bg-red-400' },
};

export function ChannelsPage() {
  const [channels, setChannels] = useState<ChannelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await fetchJSON<ChannelInfo[]>('/admin/channels');
      setChannels(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggle = async (channelId: string, enabled: boolean) => {
    setToggling(channelId);
    try {
      await putJSON(`/admin/channels/${channelId}/toggle`, { enabled });
      // 短暂延迟后刷新，等待状态更新
      setTimeout(load, 1000);
    } catch (e) {
      console.error(e);
    } finally {
      setToggling(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-6 flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-6">
      <div className="flex items-center gap-2 mb-6">
        <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
          <Radio className="w-4.5 h-4.5 text-indigo-600" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-gray-800">通道管理</h1>
          <p className="text-xs text-gray-400">管理 IM 通道连接，启用后可通过飞书等平台与助手交互</p>
        </div>
      </div>

      <div className="space-y-3">
        {channels.map((ch) => {
          const st = STATUS_MAP[ch.status] || STATUS_MAP.stopped;
          return (
            <div
              key={ch.channel_id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-gray-800 text-sm">{ch.display_name}</span>
                  <span className="text-[11px] text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded-md font-mono">
                    {ch.channel_type}
                  </span>
                  <span className={`flex items-center gap-1 text-[11px] font-medium ${st.color}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${st.dot} ${ch.status === 'running' ? 'animate-pulse' : ''}`} />
                    {st.label}
                  </span>
                </div>
                <button
                  onClick={() => toggle(ch.channel_id, !ch.enabled)}
                  disabled={toggling === ch.channel_id}
                  className="flex items-center gap-1.5 transition-transform duration-150 hover:scale-105 active:scale-95 disabled:opacity-50"
                >
                  {toggling === ch.channel_id ? (
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  ) : ch.enabled ? (
                    <ToggleRight className="w-8 h-8 text-blue-600" />
                  ) : (
                    <ToggleLeft className="w-8 h-8 text-gray-300" />
                  )}
                </button>
              </div>

              <p className="text-xs text-gray-500 mb-3 leading-relaxed">{ch.description}</p>

              {ch.status === 'error' && ch.status_message && (
                <p className="text-xs text-red-500 mb-3 bg-red-50 rounded-lg px-3 py-2">
                  {ch.status_message}
                </p>
              )}

              <Link
                to={`/admin/channels/${ch.channel_id}`}
                className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                配置 <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          );
        })}

        {channels.length === 0 && (
          <div className="text-center py-20 text-gray-400 text-sm">
            <Radio className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p>暂无可用通道</p>
          </div>
        )}
      </div>
    </div>
  );
}
