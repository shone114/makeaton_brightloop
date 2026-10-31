import React, { useState } from 'react';
import * as api from '../../api';
import Modal, { Field, inputCls, selectCls } from './Modal';

export default function RecordPaymentModal({ invoice, onClose, onPaid, toast }) {
  const [method, setMethod] = useState('credit_card');
  const [amount, setAmount] = useState(String(Number(invoice?.balance_due ?? invoice?.total ?? 0).toFixed(2)));
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    const parsedAmount = parseFloat(amount) || 0;

    // Trigger optimistic update on parent table instantly
    if (onPaid) {
      onPaid(parsedAmount);
    }

    try {
      await api.recordPayment({
        invoice_id: invoice.id,
        method,
        amount: parsedAmount,
        payment_date: date,
        note: note || `Payment for ${invoice.number}`,
      });
      toast(`Payment recorded for ${invoice.number}`, 'ok');
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
      onClose();
    }
  }

  return (
    <Modal title={`Record Payment — ${invoice?.number}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Payment Method">
          <select value={method} onChange={(e) => setMethod(e.target.value)} className={selectCls}>
            <option value="credit_card">Credit Card</option>
            <option value="bank_transfer">Bank Transfer</option>
            <option value="check">Check</option>
            <option value="other">Other</option>
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Amount ($)">
            <input
              type="number"
              step="0.01"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="Payment Date">
            <input
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="Reference Note (optional)">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. TXN-99827361"
            className={inputCls}
          />
        </Field>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-40"
        >
          {loading ? 'Recording…' : 'Record & Mark Paid'}
        </button>
      </form>
    </Modal>
  );
}
