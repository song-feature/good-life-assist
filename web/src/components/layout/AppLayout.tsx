import { ChatPanel } from './ChatPanel';
import { ModulePanel } from './ModulePanel';

export function AppLayout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <div className="w-[400px] shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <ChatPanel />
      </div>
      <div className="flex-1 overflow-auto">
        <ModulePanel />
      </div>
    </div>
  );
}
