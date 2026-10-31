import React, { useEffect, useState, useCallback } from 'react';
import * as api from '../api';
import NewSubscriptionModal from './modals/NewSubscriptionModal';

const STATUS_BADGES = {
  active: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80',
  confirmed: 'bg-zinc-800 text-zinc-200 border-zinc-700',
  quotation: 'bg-amber-950/60 text-amber-400 border-amber-800/80',
  draft: 'bg-zinc-900 text-zinc-400 border-zinc-800',
  closed: 'bg-rose-950/60 text-rose-400 border-rose-800/80',
  paused: 'bg-yellow-950/60 text-yellow-400 border-yellow-800/80',
};

const STATUS_TABS = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active' },
  { id: 'confirmed', label: 'Confirmed' },
  { id: 'quotation', label: 'Quotation' },
  { id: 'draft', label: 'Draft' },
  { id: 'paused', label: 'Paused' },
  { id: 'closed', label: 'Closed' },
];

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Subscriptions({ user, toast }) {
  const [subs, setSubs] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showNew, setShowNew] = useState(false);

  // Dropdown options
  const [customers, setCustomers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);

  const loadData = useCallback(async () => {
    // SWR: Instant load from cache (0ms) + background revalidation
    api.getSubscriptions({ page, size: 25, status, search }, (fresh) => {
      setSubs(fresh.items || []);
      setTotal(fresh.total || 0);
      setPages(fresh.pages || 1);
    }).then(({ data, isStale }) => {
      if (data) {
        setSubs(data.items || []);
        setTotal(data.total || 0);
        setPages(data.pages || 1);
      }
      if (!isStale && !data) setLoading(false);
    }).catch((err) => toast(err.message, 'err'));
  }, [page, status, search, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (user?.role === 'admin' || user?.role === 'staff') {
      api.getUsers('customer', 100).then(({ data }) => setCustomers(data || []));
      api.getPlans(1, 100).then(({ data }) => setPlans(data?.items || []));
      api.getProducts(1, 100).then(({ data }) => setProducts(data?.items || []));
    }
  }, [user]);

  // OPTIMISTIC STATUS UPDATE: UI responds instantly in 0ms!
  async function handleStatusTransition(subId, nextStatus) {
    const prevSubs = [...subs];
    // 1. Instant client update (0ms)
    setSubs((current) =>
      current.map((s) => (s.id === subId ? { ...s, status: nextStatus } : s))
    );
    toast(`Status updated to ${nextStatus}`, 'ok');

    // 2. Background database write
    try {
      await api.updateSubStatus(subId, nextStatus);
    } catch (err) {
      // Rollback on server error
      setSubs(prevSubs);
      toast(`Failed to update status: ${err.message}`, 'err');
    }
  }

  // OPTIMISTIC BILL NOW
  async function handleBillNow(sub) {
    toast(`Billing engine generated invoice for ${sub.number}…`, 'info');
    try {
      const inv = await api.generateInvoice(sub.id);
      await api.confirmInvoice(inv.id);
      toast(`Invoice ${inv.number} confirmed.`, 'ok');
      loadData();
    } catch (err) {
      toast(err.message, 'err');
    }
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  }

  const role = user?.role;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 antialiased">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-[#1d202d]">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Subscriptions & Quotations</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Pipeline lifecycle: Draft &rarr; Quotation &rarr; Confirmed &rarr; Active &rarr; Closed &bull; {total.toLocaleString()} records
          </p>
        </div>
        {(role === 'admin' || role === 'staff') && (
          <button
            onClick={() => setShowNew(true)}
            className="px-3.5 py-2 bg-white hover:bg-zinc-200 text-zinc-950 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5 self-start sm:self-auto"
          >
            <span>+</span> Create Subscription
          </button>
        )}
      </div>

      {/* Control Bar: Filters & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Status Pills */}
        <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-thin">
          {STATUS_TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setStatus(t.id);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition whitespace-nowrap ${
                status === t.id
                  ? 'bg-zinc-100 text-zinc-950 font-semibold shadow-sm'
                  : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-[#1d202d]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex gap-1.5 shrink-0">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search sub #, customer…"
            className="bg-[#10121a] border border-[#1d202d] rounded-md px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-500 w-full sm:w-60"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-[#1d202d] text-zinc-300 text-xs font-medium rounded-md transition"
          >
            Search
          </button>
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                setSearchInput('');
                setPage(1);
              }}
              className="px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-[#1d202d] text-zinc-400 text-xs rounded-md transition"
            >
              &times;
            </button>
          )}
        </form>
      </div>

      {/* Table */}
      <div className="bg-[#10121a] border border-[#1d202d] rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#1d202d] bg-[#0c0d13] text-zinc-400">
                <th className="text-left px-4 py-3 font-medium">Sub #</th>
                <th className="text-left px-4 py-3 font-medium">Customer</th>
                <th className="text-left px-4 py-3 font-medium">Plan & Terms</th>
                <th className="text-left px-4 py-3 font-medium">Period</th>
                <th className="text-right px-4 py-3 font-medium">Contract Value</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                {(role === 'admin' || role === 'staff') && (
                  <th className="text-right px-4 py-3 font-medium">Quick Transition</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1d202d]/70">
              {subs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-8 text-center text-zinc-400">
                    No subscriptions found.
                  </td>
                </tr>
              ) : (
                subs.map((sub) => (
                  <tr key={sub.id} className="hover:bg-zinc-900/40 transition">
                    <td className="px-4 py-3 font-mono text-zinc-200 font-semibold whitespace-nowrap">
                      {sub.number}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-zinc-200">{sub.customer_name || 'Customer'}</div>
                      <div className="text-[11px] text-zinc-400 font-mono">{sub.customer_email || '—'}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-zinc-200">{sub.plan_name || 'Custom Plan'}</div>
                      <div className="text-[11px] text-zinc-400 capitalize">
                        {sub.billing_period || 'monthly'} &bull; Net {sub.payment_terms_days || 15}d
                      </div>
                    </td>
                    <td className="px-4 py-3 text-zinc-300 font-mono whitespace-nowrap text-[11px]">
                      <div>{sub.start_date ? String(sub.start_date).slice(0, 10) : '—'}</div>
                      <div className="text-zinc-400">to {sub.end_date ? String(sub.end_date).slice(0, 10) : 'Open'}</div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-zinc-100 tabular-nums">
                      ${fmt(sub.total_amount)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-medium border capitalize whitespace-nowrap ${STATUS_BADGES[sub.status] || STATUS_BADGES.draft}`}>
                        {sub.status}
                      </span>
                    </td>
                    {(role === 'admin' || role === 'staff') && (
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <select
                            value={sub.status}
                            onChange={(e) => handleStatusTransition(sub.id, e.target.value)}
                            className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-[11px] text-zinc-200 focus:outline-none focus:border-zinc-500 font-medium cursor-pointer"
                          >
                            <option value="draft">Draft</option>
                            <option value="quotation">Quotation</option>
                            <option value="confirmed">Confirmed</option>
                            <option value="active">Active</option>
                            <option value="paused">Paused</option>
                            <option value="closed">Closed</option>
                          </select>

                          {sub.status === 'active' && (
                            <button
                              onClick={() => handleBillNow(sub)}
                              className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded text-[11px] font-medium transition"
                              title="Generate next period invoice immediately"
                            >
                              Bill Now
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#1d202d] bg-[#0c0d13] text-xs text-zinc-400">
            <span>
              Page <strong className="text-zinc-200">{page}</strong> of <strong className="text-zinc-200">{pages}</strong> ({total.toLocaleString()} items)
            </span>
            <div className="flex gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 border border-[#1d202d] rounded text-zinc-300 disabled:opacity-30 transition"
              >
                &larr; Prev
              </button>
              <button
                disabled={page >= pages}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 border border-[#1d202d] rounded text-zinc-300 disabled:opacity-30 transition"
              >
                Next &rarr;
              </button>
            </div>
          </div>
        )}
      </div>

      {showNew && (
        <NewSubscriptionModal
          customers={customers}
          plans={plans}
          products={products}
          onClose={() => setShowNew(false)}
          onCreated={() => {
            setShowNew(false);
            loadData();
          }}
          toast={toast}
        />
      )}
    </div>
  );
}
