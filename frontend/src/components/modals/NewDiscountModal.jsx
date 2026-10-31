import React, { useState } from 'react';
import * as api from '../../api';
import Modal, { Field, inputCls, selectCls } from './Modal';

export default function NewDiscountModal({ products, onClose, onSaved, toast }) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [type, setType] = useState('percentage');
  const [value, setValue] = useState('');
  const [minAmt, setMinAmt] = useState('');
  const [limit, setLimit] = useState('100');
  const [start, setStart] = useState(new Date().toISOString().slice(0, 10));
  const [end, setEnd] = useState(new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10));
  const [prodId, setProdId] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    const payload = {
      name: name.trim(),
      code: code.trim().toUpperCase(),
      discount_type: type,
      value: parseFloat(value),
      min_purchase_amount: minAmt ? parseFloat(minAmt) : 0,
      usage_limit: parseInt(limit, 10),
      start_date: start,
      end_date: end,
      product_ids: prodId ? [parseInt(prodId, 10)] : [],
    };

    // Optimistic fallback representation
    const optimisticDiscount = {
      id: 'temp-' + Date.now(),
      ...payload,
      current_usage: 0,
      is_active: true,
      created_at: new Date().toISOString(),
    };

    try {
      const res = await api.createDiscount(payload);
      toast(`Discount rule "${name}" created`, 'ok');
      onSaved(res || optimisticDiscount);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Create Discount Rule" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Discount Name">
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Black Friday 20%"
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Coupon Code">
            <input
              type="text"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="BF2026"
              className={inputCls}
            />
          </Field>
          <Field label="Applicable Product (optional)">
            <select value={prodId} onChange={(e) => setProdId(e.target.value)} className={selectCls}>
              <option value="">All Products</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Type">
            <select value={type} onChange={(e) => setType(e.target.value)} className={selectCls}>
              <option value="percentage">Percentage (%)</option>
              <option value="fixed_amount">Fixed Amount ($)</option>
            </select>
          </Field>
          <Field label="Value">
            <input
              type="number"
              step="0.01"
              required
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={type === 'percentage' ? '10' : '50'}
              className={inputCls}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Min Purchase Amount ($)">
            <input
              type="number"
              step="0.01"
              value={minAmt}
              onChange={(e) => setMinAmt(e.target.value)}
              placeholder="0.00"
              className={inputCls}
            />
          </Field>
          <Field label="Usage Limit">
            <input
              type="number"
              min="1"
              required
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className={inputCls}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start Date">
            <input type="date" required value={start} onChange={(e) => setStart(e.target.value)} className={inputCls} />
          </Field>
          <Field label="End Date">
            <input type="date" required value={end} onChange={(e) => setEnd(e.target.value)} className={inputCls} />
          </Field>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-40"
        >
          {loading ? 'Saving…' : 'Create Discount'}
        </button>
      </form>
    </Modal>
  );
}
