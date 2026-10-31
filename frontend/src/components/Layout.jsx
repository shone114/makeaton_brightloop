import React from 'react';
import * as api from '../api';

const NAV_ITEMS = {
  admin: [
    { id: 'dashboard', label: 'Overview', icon: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z' },
    { id: 'subscriptions', label: 'Subscriptions', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
    { id: 'invoices', label: 'Invoices & Billing', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
    { id: 'products', label: 'Catalog & Plans', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
    { id: 'staff', label: 'Staff Directory', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' },
  ],
  staff: [
    { id: 'dashboard', label: 'Overview', icon: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z' },
    { id: 'subscriptions', label: 'Subscriptions', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
    { id: 'invoices', label: 'Invoices & Billing', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
    { id: 'products', label: 'Catalog & Plans', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
  ],
  customer: [
    { id: 'portal', label: 'Account Portal', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  ],
};

export default function Layout({ user, active, onNav, onSignOut, toast, children }) {
  const role = user?.role || 'customer';
  const links = NAV_ITEMS[role] || NAV_ITEMS.customer;

  const handleExport = async (type) => {
    try {
      toast(`Exporting ${type} (.csv)…`, 'info');
      if (type === 'subscriptions') await api.exportSubscriptions();
      else await api.exportInvoices();
      toast('Export downloaded', 'ok');
    } catch (err) {
      toast(err.message, 'err');
    }
  };

  return (
    <div className="flex h-screen bg-[#090a0f] text-zinc-100 antialiased overflow-hidden select-none">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-[#0e1017] border-r border-[#1d202d] flex flex-col justify-between">
        <div>
          {/* Workspace Branding */}
          <div className="h-14 px-4 flex items-center justify-between border-b border-[#1d202d]">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded bg-white text-zinc-950 font-bold text-xs flex items-center justify-center tracking-wider shadow-sm">
                B
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-white tracking-tight block truncate">
                  Brightloop
                </span>
                <span className="text-[10px] text-zinc-400 font-medium block">
                  Console &bull; Neon DB
                </span>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="px-2.5 py-4">
            <p className="px-2.5 text-[10px] font-semibold text-zinc-400 uppercase tracking-widest mb-1.5">
              Menu
            </p>
            <nav className="space-y-0.5">
              {links.map((item) => {
                const isActive = active === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNav(item.id)}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-zinc-800 text-white font-semibold border border-zinc-700/80 shadow-sm'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 border border-transparent'
                    }`}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={isActive ? '2' : '1.75'}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-zinc-400'}`}
                    >
                      <path d={item.icon} />
                    </svg>
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Footer Area */}
        <div className="p-2.5 border-t border-[#1d202d] space-y-2">
          {(role === 'admin' || role === 'staff') && (
            <div className="grid grid-cols-2 gap-1">
              <button
                onClick={() => handleExport('subscriptions')}
                className="py-1 px-1.5 text-[10px] font-medium text-zinc-400 hover:text-zinc-200 bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 rounded transition text-center truncate"
              >
                &darr; Subs CSV
              </button>
              <button
                onClick={() => handleExport('invoices')}
                className="py-1 px-1.5 text-[10px] font-medium text-zinc-400 hover:text-zinc-200 bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 rounded transition text-center truncate"
              >
                &darr; Invoices CSV
              </button>
            </div>
          )}

          {/* User profile */}
          <div className="p-2 rounded-lg bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <div className="min-w-0 pr-1.5">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-zinc-200 truncate block">
                  {user?.name || 'User'}
                </span>
                <span className="text-[9px] font-bold uppercase tracking-wider px-1 py-0.2 rounded text-zinc-300 bg-zinc-800 border border-zinc-700">
                  {role}
                </span>
              </div>
              <span className="text-[10px] text-zinc-400 truncate block font-mono">
                {user?.email}
              </span>
            </div>

            <button
              onClick={onSignOut}
              title="Sign out"
              className="text-zinc-400 hover:text-rose-400 p-1 rounded hover:bg-zinc-800 transition"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="h-14 px-6 border-b border-[#1d202d] bg-[#090a0f] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400 font-medium">Brightloop</span>
            <span className="text-zinc-600">/</span>
            <span className="text-xs text-zinc-200 font-semibold capitalize tracking-wide">
              {active}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400 bg-zinc-900 border border-zinc-800 px-2.5 py-1 rounded">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>Neon Live &bull; Sub-100ms</span>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto scrollbar-thin bg-[#090a0f]">
          {children}
        </main>
      </div>
    </div>
  );
}
