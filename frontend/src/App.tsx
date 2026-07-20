import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ItemPage from './features/learn/ItemPage';
import PathPage from './features/learn/PathPage';
import PlayPage from './features/play/PlayPage';
import { AuthProvider, useAuth } from './lib/auth';
import AdminPage from './pages/AdminPage';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import GamesPage from './pages/GamesPage';
import SettingsPage from './pages/SettingsPage';

function Protected() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="font-display italic text-muted">Opening the Study…</p>
      </main>
    );
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<Protected />}>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/learn" replace />} />
              <Route path="/learn" element={<PathPage />} />
              <Route path="/learn/:slug" element={<ItemPage />} />
              <Route path="/play" element={<PlayPage />} />
              <Route path="/games" element={<GamesPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
