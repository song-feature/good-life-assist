import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { AdminPage } from './pages/admin/AdminPage';
import { ModuleConfigPage } from './pages/admin/ModuleConfigPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/modules/:moduleId" element={<ModuleConfigPage />} />
      </Routes>
    </BrowserRouter>
  );
}
