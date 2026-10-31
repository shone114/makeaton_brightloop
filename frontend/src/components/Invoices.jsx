import React, { useEffect, useState, useCallback } from 'react';
import * as api from '../api';
import RecordPaymentModal from './modals/RecordPaymentModal';

const STATUS_BADGES = {
  paid: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80',
  confirmed: 'bg-zinc-800 text-zinc-200 border-zinc-700',
  draft: 'bg-zinc-900 text-zinc-400 border-zinc-800',
  cancelled: 'bg-rose-950/60 text-rose-400 border-rose-800/80',
};

const FILTERS = [
  { id: 'all', label: 'All Invoices' },
  { id: 'confirmed', label: 'Confirmed' },
  { id: 'paid', label: 'Paid' },
  { id: 'draft', label: 'Draft' },
  { id: 'overdue', label: 'Overdue' },
];

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Invoices({ user, toast }) {
  const [invoices, setInvoices] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState('all');
  const [payInvoice, setPayInvoice] = useState(null);
  const [running, setRunning] = useState(false);

  const loadData = useCallback(async () => {
    const overdue = filter === 'overdue';
    const status = overdue ? '' : filter;

    // SWR: Instant load from cache (0ms) + background revalidation
    api.getInvoices({ page, size: 25, status, overdue }, (fresh) => {
      setInvoices(fresh.items || []);
      setTotal(fresh.total || 0);
      setPages(fresh.pages || 1);
    }).then(({ data }) => {
      if (data) {
        setInvoices(data.items || []);
        setTotal(data.total || 0);
        setPages(data.pages || 1);
      }
    }).catch((err) => toast(err.message, 'err'));
  }, [page, filter, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleRunBulk() {
    setRunning(true);
    toast('Running billing engine across all due subscriptions…', 'info');
    try {
      const res = await api.generateBulk();
      toast(`Batch completed: ${res.generated_count ?? 0} invoices generated.`, 'ok');
      await loadData();
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setRunning(false);
    }
  }

  async function handleDownloadPdf(inv) {
    try {
      toast(`Preparing PDF for ${inv.number}…`, 'info');
      await api.downloadPdf(inv.id, inv.number || 'INV');
      toast('PDF downloaded', 'ok');
    } catch (err) {
      toast(err.message, 'err');
    }
  }

  async function handleSendEmail(inv) {
    try {
      toast(`Dispatching invoice ${inv.number} via Resend…`, 'info');
      const res = await api.sendInvoiceEmail(inv.id);
      toast(res.message || 'Invoice emailed successfully', 'ok');
      await loadData();
    } catch (err) {
      toast(err.message, 'err');
    }
  }

  // OPTIMISTIC PAYMENT RECORDING: UI updates in 0ms!
  function handleOptimisticPayment(invoiceId, paymentAmount) {
    setInvoices((current) =>
      current.map((inv) => {
        if (inv.id === invoiceId) {
          const newBal = Math.max(0, (inv.balance_due || inv.total) - paymentAmount);
          return {
            ...inv,
            balance_due: newBal,
            status: newBal <= 0 ? 'paid' : inv.status,
            paid_amount: (inv.paid_amount || 0) + paymentAmount,
          };
        }
        return inv;
      })
    );
  }

  const role = user?.role;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 antialiased">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-[#1d202d]">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Invoice Ledger & Receivables</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Automated recurring invoices, tax calculations, and settlement tracking &bull; {total.toLocaleString()} total
          </p>
        </div>
        {(role === 'admin' || role === 'staff') && (
          <button
            onClick={handleRunBulk}
            disabled={running}
            className="px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 border border-[#1d202d] text-zinc-200 rounded-lg text-xs font-semibold transition disabled:opacity-40 flex items-center gap-2 self-start sm:self-auto"
          >
            {running ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin"></span>
                Processing…
              </>
            ) : (
              'Run Billing Run (Batch)'
            )}
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-thin">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => {
              setFilter(f.id);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition whitespace-nowrap ${
              filter === f.id
                ? 'bg-zinc-100 text-zinc-950 font-semibold shadow-sm'
                : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-[#1d202d]'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Invoices Table */}
      <div className="bg-[#10121a] border border-[#1d202d] rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#1d202d] bg-[#0c0d13] text-zinc-400">
                <th className="text-left px-4 py-3 font-medium">Invoice #</th>
                <th className="text-left px-4 py-3 font-medium">Customer</th>
                <th className="text-left px-4 py-3 font-medium">Invoice Date / Due</th>
                <th className="text-right px-4 py-3 font-medium">Subtotal + Tax</th>
                <th className="text-right px-4 py-3 font-medium">Total</th>
                <th className="text-right px-4 py-3 font-medium">Balance Due</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1d202d]/70">
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-4 py-8 text-center text-zinc-400">
                    No invoices found.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => {
                  const isOverdue = inv.is_overdue && inv.status !== 'paid';
                  const badgeCls = isOverdue
                    ? 'bg-rose-950/60 text-rose-400 border-rose-800/80'
                    : STATUS_BADGES[inv.status] || STATUS_BADGES.draft;

                  const subtotal = inv.subtotal ?? 0;
                  const tax = inv.tax_total ?? 0;

                  return (
                    <tr key={inv.id} className="hover:bg-zinc-900/40 transition">
                      <td className="px-4 py-3 font-mono text-zinc-200 font-semibold whitespace-nowrap">
                        {inv.number}
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-zinc-200">{inv.customer_name || 'Customer'}</div>
                        <div className="text-[11px] text-zinc-400 font-mono">{inv.customer_email || '—'}</div>
                      </td>
                      <td className="px-4 py-3 text-zinc-300 font-mono text-[11px] whitespace-nowrap">
                        <div>Inv: {inv.invoice_date ? String(inv.invoice_date).slice(0, 10) : '—'}</div>
                        <div className={isOverdue ? 'text-rose-400 font-medium' : 'text-zinc-500'}>
                          Due: {inv.due_date ? String(inv.due_date).slice(0, 10) : '—'}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-zinc-400 whitespace-nowrap">
                        ${fmt(subtotal)} + ${fmt(tax)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-zinc-100 tabular-nums whitespace-nowrap">
                        ${fmt(inv.total)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold whitespace-nowrap">
                        <span className={(inv.balance_due || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}>
                          ${fmt(inv.balance_due)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium border capitalize ${badgeCls}`}>
                          {isOverdue ? 'Overdue' : inv.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleDownloadPdf(inv)}
                            className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-300 rounded text-xs transition"
                            title="Download PDF"
                          >
                            PDF
                          </button>

                          {(role === 'admin' || role === 'staff') && (
                            <>
                              <button
                                onClick={() => handleSendEmail(inv)}
                                className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-300 rounded text-xs transition"
                                title="Send via Email"
                              >
                                Email
                              </button>

                              {inv.status !== 'paid' && (
                                <button
                                  onClick={() => setPayInvoice(inv)}
                                  className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-emerald-400 border border-zinc-700 rounded text-xs font-medium transition"
                                  title="Record Payment"
                                >
                                  Record Pay
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#1d202d] bg-[#0c0d13] text-xs text-zinc-400">
            <span>
              Page <strong className="text-zinc-200">{page}</strong> of <strong className="text-zinc-200">{pages}</strong> ({total.toLocaleString()} records)
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

      {payInvoice && (
        <RecordPaymentModal
          invoice={payInvoice}
          onClose={() => setPayInvoice(null)}
          onPaid={(amt) => {
            handleOptimisticPayment(payInvoice.id, amt);
            setPayInvoice(null);
            loadData();
          }}
          toast={toast}
        />
      )}
    </div>
  );
}
