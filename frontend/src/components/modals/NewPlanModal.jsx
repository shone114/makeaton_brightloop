import React, { useState } from 'react';
import * as api from '../../api';
import Modal, { Field, inputCls, selectCls } from './Modal';

export default function NewPlanModal({ onClose, onSaved, toast }) {
  const [name, setName] = useState('');
  const [period, setPeriod] = useState('monthly');
  const [amount, setAmount] = useState('49.00');
  const [minQty, setMinQty] = useState('1');
  const [from, setFrom] = useState(new Date().toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10));
  const [pausable, setPausable] = useState(true);
  const [closable, setClosable] = useState(true);
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    const payload = {
      name: name.trim(),
      billing_period: period,
      amount: parseFloat(amount),
      min_quantity: parseInt(minQty, 10),
      available_from: from,
      available_to: to,
      is_pausable: pausable,
      is_closable_early: closable,
    };

    const optimisticPlan = {
      id: 'temp-' + Date.now(),
      ...payload,
      is_active: true,
      created_at: new Date().toISOString(),
    };

    try {
      const res = await api.createPlan(payload);
      toast(`Billing plan "${name}" created`, 'ok');
      onSaved(res || optimisticPlan);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Configure Billing Plan" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Plan Name">
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Pro Monthly"
            className={inputCls}
          />
        </Field>
        <Field label="Billing Cadence">
          <select value={period} onChange={(e) => setPeriod(e.target.value)} className={selectCls}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
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
          <Field label="Min Quantity">
            <input
              type="number"
              min="1"
              required
              value={minQty}
              onChange={(e) => setMinQty(e.target.value)}
              className={inputCls}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Available From">
            <input type="date" required value={from} onChange={(e) => setFrom(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Available To">
            <input type="date" required value={to} onChange={(e) => setTo(e.target.value)} className={inputCls} />
          </Field>
        </div>
        <div className="flex gap-4 text-xs text-zinc-300">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={pausable}
              onChange={(e) => setPausable(e.target.checked)}
              className="accent-zinc-100"
            />
            Pausable
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={closable}
              onChange={(e) => setClosable(e.target.checked)}
              className="accent-zinc-100"
            />
            Closable Early
          </label>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-40"
        >
          {loading ? 'Saving…' : 'Create Plan'}
        </button>
      </form>
    </Modal>
  );
}
