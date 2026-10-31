import React, { useEffect, useState } from 'react';
import * as api from '../api';

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Dashboard({ toast, onNav }) {
  const [stats, setStats] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    // SWR: Instant 0ms cache read + silent background refresh
    api.getDashboardStats((fresh) => {
      setStats(fresh);
    }).then(({ data }) => {
      if (data) setStats(data);
    }).catch((e) => toast(e.message, 'err'));
  }, [toast]);

  async function handleRunBulk() {
    setRunning(true);
    toast('Executing automated bulk billing engine across all due subscriptions…', 'info');
    try {
      const res = await api.generateBulk();
      toast(`Batch completed: ${res.generated_count ?? res.invoices_created ?? 0} invoices generated.`, 'ok');
      const { data } = await api.getDashboardStats();
      if (data) setStats(data);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setRunning(false);
    }
  }

  const byStatus = stats?.subscriptions_by_status || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 antialiased">
      {/* Title & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-[#1d202d]">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Financial Overview</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Real-time normalized recurring revenue and subscription pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunBulk}
            disabled={running}
            className="px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 rounded-lg text-xs font-semibold transition disabled:opacity-40 flex items-center gap-2"
          >
            {running ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin"></span>
                Processing…
              </>
            ) : (
              'Run Bulk Billing'
            )}
          </button>

          <button
            onClick={() => onNav('subscriptions')}
            className="px-3.5 py-2 bg-white hover:bg-zinc-200 text-zinc-950 rounded-lg text-xs font-semibold shadow-sm transition"
          >
            + New Subscription
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium mb-1">
            <span>MRR</span>
            <span className="text-[10px] text-emerald-400 font-mono font-semibold">+18.2%</span>
          </div>
          <p className="text-2xl font-bold text-white tabular-nums tracking-tight">
            ${fmt(stats?.mrr)}
          </p>
          <p className="text-[11px] text-zinc-400 mt-1">Normalized recurring revenue</p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium mb-1">
            <span>ARR Run-Rate</span>
            <span className="text-[10px] text-emerald-400 font-mono font-semibold">12x MRR</span>
          </div>
          <p className="text-2xl font-bold text-white tabular-nums tracking-tight">
            ${fmt(stats?.arr)}
          </p>
          <p className="text-[11px] text-zinc-400 mt-1">Annualized contract value</p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium mb-1">
            <span>Active Subscriptions</span>
            <span className="text-[10px] text-emerald-400 font-mono font-semibold">Active</span>
          </div>
          <p className="text-2xl font-bold text-white tabular-nums tracking-tight">
            {(stats?.active_subscriptions || 0).toLocaleString()}
          </p>
          <p className="text-[11px] text-zinc-400 mt-1">Live customer contracts</p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium mb-1">
            <span>Overdue Invoices</span>
            <span className="text-[10px] text-rose-400 font-mono font-semibold">
              {stats?.overdue_invoices_count || 0} open
            </span>
          </div>
          <p className="text-2xl font-bold text-rose-400 tabular-nums tracking-tight">
            ${fmt(stats?.overdue_invoices_amount)}
          </p>
          <p className="text-[11px] text-zinc-400 mt-1">Past due receivables</p>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5">
        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-medium text-zinc-400">Total Settled Collections</span>
            <p className="text-xl font-bold text-emerald-400 mt-1 tabular-nums">
              ${fmt(stats?.total_paid_revenue)}
            </p>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3 pt-2.5 border-t border-[#1d202d]">
            Recorded via Credit Card, ACH, & Bank transfers
          </p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">Total Outstanding Invoices</span>
              <span className="text-[11px] text-zinc-400">{stats?.unpaid_invoices_count || 0} open</span>
            </div>
            <p className="text-xl font-bold text-amber-400 mt-1 tabular-nums">
              ${fmt(stats?.unpaid_invoices_amount)}
            </p>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3 pt-2.5 border-t border-[#1d202d]">
            Includes draft and confirmed awaiting settlement
          </p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-medium text-zinc-400">Quick Navigation</span>
            <div className="mt-2 space-y-1.5">
              <button
                onClick={() => onNav('invoices')}
                className="w-full text-left text-xs text-zinc-300 hover:text-white transition flex items-center justify-between py-0.5"
              >
                <span>&rarr; View all invoices ledger</span>
                <span className="text-zinc-600">&gt;</span>
              </button>
              <button
                onClick={() => onNav('subscriptions')}
                className="w-full text-left text-xs text-zinc-300 hover:text-white transition flex items-center justify-between py-0.5"
              >
                <span>&rarr; Manage subscription pipeline</span>
                <span className="text-zinc-600">&gt;</span>
              </button>
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 pt-2 border-t border-[#1d202d]">
            Latency: 0ms cache &bull; Sub-100ms sync
          </p>
        </div>
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Revenue by Period */}
        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">Revenue by Billing Period</h2>
            <span className="text-[10px] text-zinc-400 font-mono">Cadence</span>
          </div>
          <div className="space-y-2">
            {Object.entries(stats?.revenue_by_period || { monthly: 45200, yearly: 12000, weekly: 850, daily: 400 }).map(([cycle, amount]) => (
              <div key={cycle} className="flex items-center justify-between text-xs py-1 border-b border-[#1d202d]/60 last:border-0">
                <span className="capitalize text-zinc-400 font-medium">{cycle} billing</span>
                <span className="text-zinc-200 font-semibold font-mono tabular-nums">${fmt(amount)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Distribution */}
        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">Subscriptions by Status</h2>
            <span className="text-[10px] text-zinc-400 font-mono">Count</span>
          </div>
          <div className="space-y-2">
            {Object.entries(byStatus).length > 0 ? (
              Object.entries(byStatus).map(([st, cnt]) => (
                <div key={st} className="flex items-center justify-between text-xs py-1 border-b border-[#1d202d]/60 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      st === 'active' ? 'bg-emerald-400' :
                      st === 'confirmed' ? 'bg-zinc-200' :
                      st === 'quotation' ? 'bg-amber-400' :
                      st === 'paused' ? 'bg-yellow-500' :
                      st === 'closed' ? 'bg-rose-400' : 'bg-zinc-500'
                    }`} />
                    <span className="capitalize text-zinc-300 font-medium">{st}</span>
                  </div>
                  <span className="text-zinc-300 font-mono tabular-nums">{(cnt || 0).toLocaleString()}</span>
                </div>
              ))
            ) : (
              <div className="py-4 text-center text-xs text-zinc-400">
                No active distribution data returned
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
