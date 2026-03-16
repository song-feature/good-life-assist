import { Link, useLocation } from 'react-router-dom';
import { Settings, Brain, Blocks, BarChart3, ShieldAlert, Radio, ArrowLeft } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/admin', label: '系统总览', icon: Settings },
  { path: '/admin/models', label: '模型管理', icon: Brain },
  { path: '/admin/modules/stock', label: '模块配置', icon: Blocks },
  { divider: true, label: '股票模块' },
  { path: '/admin/stock/portfolio', label: '持仓总览', icon: BarChart3 },
  { path: '/admin/stock/options', label: '期权墙', icon: ShieldAlert },
  { divider: true, label: '通道管理' },
  { path: '/admin/channels', label: '通道列表', icon: Radio },
] as const;

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-gray-50/70 flex">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 bg-white border-r border-gray-100 flex flex-col">
        <div className="px-4 py-4 border-b border-gray-100">
          <Link to="/" className="flex items-center gap-2 text-gray-500 hover:text-blue-600 transition-colors text-xs font-medium">
            <ArrowLeft className="w-3.5 h-3.5" />
            返回主界面
          </Link>
          <h1 className="mt-3 text-sm font-bold text-gray-800">系统管理</h1>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV_ITEMS.map((item, i) => {
            if ('divider' in item) {
              return (
                <div key={i} className="pt-3 pb-1.5 px-3">
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">{item.label}</span>
                </div>
              );
            }
            const Icon = item.icon;
            const active = pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${
                  active
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
