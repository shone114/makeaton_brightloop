import React, { useState, useEffect, useCallback } from 'react';
import * as api from './api';
import AuthScreen from './components/AuthScreen';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Subscriptions from './components/Subscriptions';
import Invoices from './components/Invoices';
import Products from './components/Products';
import Staff from './components/Staff';
import CustomerPortal from './components/CustomerPortal';

// ─── Toast ─────────────────────────────────────────────────────────────────

function ToastBanner({ toasts }) {
  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div key={t.id}
          className={`px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg transition-all
            ${t.type === 'ok' ? 'bg-emerald-700 text-white' :
              t.type === 'err' ? 'bg-rose-700 text-white' :
              'bg-slate-700 text-slate-100'}`}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

// ─── App ───────────────────────────────────────────────────────────────────

export default function App() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('bl_user')); } catch { return null; }
  });
  const [tab, setTab] = useState(() => {
    try {
      const u = JSON.parse(localStorage.getItem('bl_user'));
      return u?.role === 'customer' ? 'portal' : 'dashboard';
    } catch {
      return 'dashboard';
    }
  });
  const [toasts, setToasts] = useState([]);

  // Validate saved session on mount
  useEffect(() => {
    if (api.getToken()) {
      api.getMe()
        .then(u => {
          setUser(u);
          localStorage.setItem('bl_user', JSON.stringify(u));
        })
        .catch(() => {
          // Token invalid — sign out
          api.setToken('');
          localStorage.removeItem('bl_user');
          setUser(null);
        });
    }
  }, []);

  // Set default tab when user changes
  useEffect(() => {
    if (user) {
      setTab(user.role === 'customer' ? 'portal' : 'dashboard');
    }
  }, [user?.role]);

  const toast = useCallback((msg, type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts(ts => [...ts, { id, msg, type }]);
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), 4000);
  }, []);

  function handleLogin(u) {
    setUser(u);
    localStorage.setItem('bl_user', JSON.stringify(u));
    setTab(u?.role === 'customer' ? 'portal' : 'dashboard');
  }

  function handleSignOut() {
    api.setToken('');
    localStorage.removeItem('bl_user');
    localStorage.removeItem('bl_token');
    setUser(null);
    toast('Signed out', 'info');
  }

  const role = user?.role;

  function renderTab() {
    if (role === 'customer') {
      return <CustomerPortal user={user} toast={toast} />;
    }
    switch (tab) {
      case 'dashboard': return <Dashboard toast={toast} onNav={setTab} />;
      case 'subscriptions': return <Subscriptions user={user} toast={toast} />;
      case 'invoices': return <Invoices user={user} toast={toast} />;
      case 'products': return <Products user={user} toast={toast} />;
      case 'staff': return <Staff toast={toast} />;
      default: return <Dashboard toast={toast} onNav={setTab} />;
    }
  }

  return (
    <>
      <ToastBanner toasts={toasts} />
      {!user ? (
        <AuthScreen onLogin={handleLogin} toast={toast} />
      ) : (
        <Layout user={user} active={tab} onNav={setTab} onSignOut={handleSignOut} toast={toast}>
          {renderTab()}
        </Layout>
      )}
    </>
  );
}
