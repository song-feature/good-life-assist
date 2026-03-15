import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { AdminLayout } from './pages/admin/AdminLayout';
import { AdminPage } from './pages/admin/AdminPage';
import { ModuleConfigPage } from './pages/admin/ModuleConfigPage';
import { ModelManagementPage } from './pages/admin/ModelManagementPage';
import { StockPortfolioPage } from './pages/admin/StockPortfolioPage';
import { StockOptionsPage } from './pages/admin/StockOptionsPage';
import { ChannelsPage } from './pages/admin/ChannelsPage';
import { ChannelConfigPage } from './pages/admin/ChannelConfigPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />} />
        <Route path="/admin" element={<AdminLayout><AdminPage /></AdminLayout>} />
        <Route path="/admin/modules/:moduleId" element={<AdminLayout><ModuleConfigPage /></AdminLayout>} />
        <Route path="/admin/models" element={<AdminLayout><ModelManagementPage /></AdminLayout>} />
        <Route path="/admin/stock/portfolio" element={<AdminLayout><StockPortfolioPage /></AdminLayout>} />
        <Route path="/admin/stock/options" element={<AdminLayout><StockOptionsPage /></AdminLayout>} />
        <Route path="/admin/channels" element={<AdminLayout><ChannelsPage /></AdminLayout>} />
        <Route path="/admin/channels/:channelId" element={<AdminLayout><ChannelConfigPage /></AdminLayout>} />
      </Routes>
    </BrowserRouter>
  );
}
