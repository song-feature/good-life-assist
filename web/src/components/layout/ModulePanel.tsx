import { useModuleStore } from '../../stores/moduleStore';
import { StockModulePage } from '../../modules/stock/StockModulePage';
import { LayoutDashboard } from 'lucide-react';

export function ModulePanel() {
  const activeModule = useModuleStore((s) => s.activeModule);

  if (activeModule === 'stock') {
    return <StockModulePage />;
  }

  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-400">
      <LayoutDashboard className="w-16 h-16 mb-4 text-gray-200" />
      <p className="text-lg font-medium text-gray-300">功能区</p>
      <p className="text-sm mt-1">通过左侧对话触发功能模块</p>
    </div>
  );
}
