import React, { useEffect, useState, useCallback } from 'react';
import * as api from '../api';
import Modal, { Field, inputCls, selectCls } from './modals/Modal';

const STATUS_BADGES = {
  active: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80',
  confirmed: 'bg-zinc-800 text-zinc-200 border-zinc-700',
  draft: 'bg-zinc-900 text-zinc-400 border-zinc-800',
  paid: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80',
  quotation: 'bg-amber-950/60 text-amber-400 border-amber-800/80',
  closed: 'bg-rose-950/60 text-rose-400 border-rose-800/80',
  paused: 'bg-yellow-950/60 text-yellow-400 border-yellow-800/80',
};

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function CustomerPortal({ user, toast }) {
  const [stats, setStats] = useState(null);
  const [subs, setSubs] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [activeSubId, setActiveSubId] = useState(null);

  // Subscribe modal
  const [showSubscribeModal, setShowSubscribeModal] = useState(false);
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);

  const loadData = useCallback(async () => {
    // SWR: Instant load from cache (0ms) + background refresh
    api.getPortalStats((s) => setStats(s)).then(({ data }) => data && setStats(data));
    api.getPortalSubscriptions((s) => {
      setSubs(s);
      if (s.length > 0 && !activeSubId) setActiveSubId(s[0].id);
    }).then(({ data }) => {
      if (data) {
        setSubs(data);
        if (data.length > 0 && !activeSubId) setActiveSubId(data[0].id);
      }
    });
    api.getPortalInvoices((inv) => setInvoices(inv)).then(({ data }) => data && setInvoices(data));
  }, [activeSubId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load plans & products for subscribing
  const openSubscribeModal = async () => {
    try {
      const [pl, pr] = await Promise.all([
        api.getPlans(1, 100),
        api.getProducts(1, 100),
      ]);
      setPlans(pl.data?.items || []);
      setProducts(pr.data?.items || []);
      setShowSubscribeModal(true);
    } catch (err) {
      toast(err.message, 'err');
    }
  };

  const activeSub = subs.find((s) => s.id === activeSubId);
  const displayedInvoices =
    activeSubId === 'all' || !activeSubId
      ? invoices
      : invoices.filter((inv) => inv.subscription_id === activeSubId);

  async function handleDownload(inv) {
    try {
      toast('Preparing PDF download…', 'info');
      await api.downloadPdf(inv.id, inv.number || 'INV');
      toast('PDF downloaded', 'ok');
    } catch (err) {
      toast(err.message, 'err');
    }
  }

  // OPTIMISTIC TRANSITION: State updates in 0ms!
  async function handleStatusTransition(subId, nextStatus) {
    const prevSubs = [...subs];
    setSubs((current) =>
      current.map((s) => (s.id === subId ? { ...s, status: nextStatus } : s))
    );
    toast(`Subscription status updated to ${nextStatus}`, 'ok');

    try {
      await api.updateSubStatus(subId, nextStatus);
    } catch (err) {
      setSubs(prevSubs);
      toast(`Update failed: ${err.message}`, 'err');
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 antialiased">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-[#10121a] border border-[#1d202d] rounded-xl p-5">
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded">
            Customer Account Portal
          </span>
          <h1 className="text-xl font-bold text-white mt-1.5">{stats?.customer_name || user?.name}</h1>
          <p className="text-xs text-zinc-400 mt-0.5">{stats?.customer_email || user?.email}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={openSubscribeModal}
            className="px-3.5 py-2 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition"
          >
            + Subscribe to a Plan
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <p className="text-xs text-zinc-400 font-medium">Active Subscriptions</p>
          <p className="text-2xl font-bold text-white mt-1">
            {stats?.active_subscriptions ?? subs.filter((s) => s.status === 'active').length}
          </p>
          <p className="text-[11px] text-zinc-400 mt-1">{subs.length} total contracts</p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <p className="text-xs text-zinc-400 font-medium">Total Settled to Date</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">${fmt(stats?.total_paid)}</p>
          <p className="text-[11px] text-zinc-400 mt-1">All paid invoices</p>
        </div>

        <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-4">
          <p className="text-xs text-zinc-400 font-medium">Balance Due</p>
          <p className={`text-2xl font-bold mt-1 ${(stats?.balance_due || 0) > 0 ? 'text-rose-400' : 'text-zinc-300'}`}>
            ${fmt(stats?.balance_due)}
          </p>
          <p className="text-[11px] text-zinc-400 mt-1">
            {(stats?.balance_due || 0) > 0 ? 'Pending invoice settlement' : 'Account current & clear'}
          </p>
        </div>
      </div>

      {/* Main Grid: Subscriptions Selector + Invoices */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Subscriptions list */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">Your Subscriptions</h2>
            <button
              onClick={() => setActiveSubId('all')}
              className={`text-xs px-2 py-0.5 rounded transition ${
                activeSubId === 'all'
                  ? 'bg-zinc-800 text-white font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              Show All ({subs.length})
            </button>
          </div>

          {subs.length === 0 ? (
            <div className="bg-[#10121a] border border-[#1d202d] rounded-xl p-6 text-center">
              <p className="text-sm text-zinc-200 font-medium">No active subscriptions</p>
              <p className="text-xs text-zinc-400 mt-1">Select a recurring plan to get started.</p>
              <button
                onClick={openSubscribeModal}
                className="mt-3 px-3.5 py-1.5 bg-white text-zinc-950 text-xs font-semibold rounded-md transition hover:bg-zinc-200"
              >
                Browse Plans & Subscribe
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {subs.map((sub) => {
                const isSelected = activeSubId === sub.id;
                return (
                  <div
                    key={sub.id}
                    onClick={() => setActiveSubId(sub.id)}
                    className={`cursor-pointer rounded-xl border p-3.5 transition text-left ${
                      isSelected
                        ? 'bg-[#181b26] border-zinc-500 shadow-sm'
                        : 'bg-[#10121a] border-[#1d202d] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="font-mono text-xs text-zinc-300 font-semibold">{sub.number}</span>
                        <h3 className="text-sm font-semibold text-white mt-0.5 truncate">
                          {sub.plan_name || 'Recurring Plan'}
                        </h3>
                        <p className="text-[11px] text-zinc-400 capitalize mt-0.5">
                          {sub.billing_period || 'monthly'} &bull; Net {sub.payment_terms_days || 15} days
                        </p>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-medium border capitalize shrink-0 ${STATUS_BADGES[sub.status] || STATUS_BADGES.draft}`}>
                        {sub.status}
                      </span>
                    </div>

                    {/* Subscription Items */}
                    {sub.lines && sub.lines.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-[#1d202d] space-y-1">
                        {sub.lines.map((ln, idx) => (
                          <div key={idx} className="flex items-center justify-between text-[11px] text-zinc-400">
                            <span className="truncate pr-2">
                              {ln.product_name}
                              {ln.variant_label ? ` (${ln.variant_label})` : ''} &times; {ln.quantity}
                            </span>
                            <span className="text-zinc-300 font-mono">${fmt(ln.line_total)}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="mt-3 flex items-center gap-1.5 pt-2 border-t border-[#1d202d]" onClick={(e) => e.stopPropagation()}>
                      {sub.status === 'quotation' && (
                        <button
                          onClick={() => handleStatusTransition(sub.id, 'confirmed')}
                          className="px-2.5 py-1 bg-white hover:bg-zinc-200 text-zinc-950 text-[11px] font-semibold rounded transition"
                        >
                          Accept Quotation
                        </button>
                      )}
                      {sub.status === 'confirmed' && (
                        <button
                          onClick={() => handleStatusTransition(sub.id, 'active')}
                          className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-semibold rounded transition"
                        >
                          Activate Service
                        </button>
                      )}
                      {sub.status === 'active' && (
                        <>
                          <button
                            onClick={() => handleStatusTransition(sub.id, 'paused')}
                            className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 text-[11px] rounded transition"
                          >
                            Pause
                          </button>
                          <button
                            onClick={() => handleStatusTransition(sub.id, 'closed')}
                            className="px-2 py-1 bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800 text-[11px] rounded transition"
                          >
                            Cancel Plan
                          </button>
                        </>
                      )}
                      {sub.status === 'paused' && (
                        <button
                          onClick={() => handleStatusTransition(sub.id, 'active')}
                          className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-semibold rounded transition"
                        >
                          Resume Service
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Invoices for the active subscription */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
              {activeSub ? `Invoices for ${activeSub.number}` : 'All Invoices'}
            </h2>
            <span className="text-xs text-zinc-400">{displayedInvoices.length} invoices found</span>
          </div>

          <div className="bg-[#10121a] border border-[#1d202d] rounded-xl overflow-hidden shadow-lg">
            {displayedInvoices.length === 0 ? (
              <div className="p-8 text-center text-zinc-400 text-xs">
                No invoices issued for this selection yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#1d202d] bg-[#0c0d13] text-zinc-400">
                      <th className="text-left px-4 py-3 font-medium">Invoice #</th>
                      <th className="text-left px-4 py-3 font-medium">Date / Due</th>
                      <th className="text-right px-4 py-3 font-medium">Amount</th>
                      <th className="text-right px-4 py-3 font-medium">Balance</th>
                      <th className="text-left px-4 py-3 font-medium">Status</th>
                      <th className="text-right px-4 py-3 font-medium">PDF</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1d202d]/70">
                    {displayedInvoices.map((inv) => {
                      const isOverdue = inv.is_overdue && inv.status !== 'paid';
                      const badgeCls = isOverdue
                        ? 'bg-rose-950/60 text-rose-400 border-rose-800/80'
                        : STATUS_BADGES[inv.status] || STATUS_BADGES.draft;

                      return (
                        <tr key={inv.id} className="hover:bg-zinc-900/40 transition">
                          <td className="px-4 py-3 font-mono text-zinc-200 font-medium">
                            {inv.number}
                          </td>
                          <td className="px-4 py-3 text-zinc-400">
                            <div>{inv.invoice_date ? String(inv.invoice_date).slice(0, 10) : '—'}</div>
                            <div className={`text-[11px] ${isOverdue ? 'text-rose-400 font-medium' : 'text-zinc-400'}`}>
                              Due: {inv.due_date ? String(inv.due_date).slice(0, 10) : '—'}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right font-medium text-zinc-200">
                            ${fmt(inv.total)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`font-semibold ${(inv.balance_due || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                              ${fmt(inv.balance_due)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-medium border capitalize ${badgeCls}`}>
                              {isOverdue ? 'Overdue' : inv.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleDownload(inv)}
                              className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 rounded text-xs transition"
                            >
                              PDF
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Subscribe to New Plan Modal */}
      {showSubscribeModal && (
        <SubscribeModal
          plans={plans}
          products={products}
          onClose={() => setShowSubscribeModal(false)}
          onSubscribed={async () => {
            setShowSubscribeModal(false);
            await loadData();
          }}
          toast={toast}
        />
      )}
    </div>
  );
}

// ─── Modal for Customer to Subscribe ─────────────────────────────────────────

function SubscribeModal({ plans, products, onClose, onSubscribed, toast }) {
  const [planId, setPlanId] = useState(plans[0]?.id || '');
  const [productId, setProductId] = useState(products[0]?.id || '');
  const [variantId, setVariantId] = useState('');
  const [qty, setQty] = useState('1');
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [terms, setTerms] = useState('15');
  const [submitting, setSubmitting] = useState(false);

  const selectedProduct = products.find((p) => p.id === productId);
  const variants = selectedProduct?.variants || [];

  async function handleSubscribe(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const lines = productId
        ? [{ product_id: productId, variant_id: variantId || null, quantity: parseInt(qty, 10) }]
        : [];

      await api.createSubscription({
        plan_id: planId,
        start_date: startDate,
        payment_terms_days: parseInt(terms, 10),
        lines,
      });

      toast('Subscription created successfully!', 'ok');
      onSubscribed();
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Choose Your Subscription Plan" onClose={onClose}>
      <form onSubmit={handleSubscribe} className="space-y-3.5">
        <Field label="Select Plan">
          <select value={planId} onChange={(e) => setPlanId(e.target.value)} className={selectCls}>
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} — ${fmt(p.amount)} / {p.billing_period}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Choose Product / Solution">
          <select
            value={productId}
            onChange={(e) => {
              setProductId(e.target.value);
              setVariantId('');
            }}
            className={selectCls}
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} (${fmt(p.sales_price)})
              </option>
            ))}
          </select>
        </Field>

        {variants.length > 0 && (
          <Field label="Select Variant / Edition">
            <select value={variantId} onChange={(e) => setVariantId(e.target.value)} className={selectCls}>
              <option value="">Base Edition (+ $0.00)</option>
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.attribute_name}: {v.attribute_value} (+${fmt(v.price_extra)})
                </option>
              ))}
            </select>
          </Field>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Field label="Seats / Quantity">
            <input
              type="number"
              min="1"
              required
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className={inputCls}
            />
          </Field>

          <Field label="Payment Terms">
            <select value={terms} onChange={(e) => setTerms(e.target.value)} className={selectCls}>
              <option value="15">Net 15 Days</option>
              <option value="30">Net 30 Days</option>
              <option value="45">Net 45 Days</option>
            </select>
          </Field>
        </div>

        <Field label="Start Date">
          <input
            type="date"
            required
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className={inputCls}
          />
        </Field>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
        >
          {submitting ? 'Confirming…' : 'Subscribe Now'}
        </button>
      </form>
    </Modal>
  );
}
