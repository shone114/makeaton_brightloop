import React, { useState } from 'react';
import * as api from '../../api';
import Modal, { Field, inputCls, selectCls } from './Modal';

export default function NewSubscriptionModal({ customers, plans, products, onClose, onCreated, toast }) {
  const [customerId, setCustomerId] = useState(customers[0]?.id || '');
  const [planId, setPlanId] = useState(plans[0]?.id || '');
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState('');
  const [productId, setProductId] = useState('');
  const [variantId, setVariantId] = useState('');
  const [qty, setQty] = useState('1');
  const [loading, setLoading] = useState(false);

  const selectedProduct = products.find((p) => String(p.id) === String(productId));
  const variants = selectedProduct?.variants || [];

  async function submit(e) {
    e.preventDefault();
    if (!customerId || !planId) {
      toast('Please select a customer and plan', 'err');
      return;
    }
    setLoading(true);

    const lines = productId
      ? [
          {
            product_id: parseInt(productId, 10),
            variant_id: variantId ? parseInt(variantId, 10) : null,
            quantity: parseInt(qty, 10),
          },
        ]
      : [];

    const payload = {
      customer_id: parseInt(customerId, 10),
      plan_id: parseInt(planId, 10),
      start_date: startDate,
      end_date: endDate || null,
      lines,
    };

    const optimisticSub = {
      id: 'temp-' + Date.now(),
      status: 'draft',
      start_date: startDate,
      end_date: endDate || null,
      customer: customers.find((c) => String(c.id) === String(customerId)) || { id: customerId, name: 'Customer' },
      plan: plans.find((p) => String(p.id) === String(planId)) || { id: planId, name: 'Plan', billing_period: 'monthly' },
      lines: lines.map((l) => ({
        id: 'line-' + Date.now(),
        product: selectedProduct,
        quantity: l.quantity,
      })),
      created_at: new Date().toISOString(),
    };

    try {
      const res = await api.createSubscription(payload);
      toast('Subscription quotation created (Draft)', 'ok');
      onCreated(res || optimisticSub);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Create Subscription Quotation" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Customer Account">
          <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required className={selectCls}>
            <option value="">— Select Customer —</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.email})
              </option>
            ))}
          </select>
        </Field>

        <Field label="Billing Plan">
          <select value={planId} onChange={(e) => setPlanId(e.target.value)} required className={selectCls}>
            <option value="">— Select Plan —</option>
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} — ${Number(p.amount).toFixed(2)} / {p.billing_period}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Start Date">
            <input
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="End Date (optional)">
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputCls} />
          </Field>
        </div>

        <div className="border-t border-zinc-800/80 pt-3">
          <p className="text-xs text-zinc-400 font-medium mb-2">Initial Product Line</p>
          <Field label="Product">
            <select
              value={productId}
              onChange={(e) => {
                setProductId(e.target.value);
                setVariantId('');
              }}
              className={selectCls}
            >
              <option value="">— No product —</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {variants.length > 0 && (
          <Field label="Variant (optional)">
            <select value={variantId} onChange={(e) => setVariantId(e.target.value)} className={selectCls}>
              <option value="">Base / No variant</option>
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.attribute_name}: {v.attribute_value} (+${Number(v.price_extra || 0).toFixed(2)})
                </option>
              ))}
            </select>
          </Field>
        )}

        <Field label="Quantity">
          <input
            type="number"
            min="1"
            required
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className={inputCls}
          />
        </Field>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-40 mt-1"
        >
          {loading ? 'Creating…' : 'Create Subscription'}
        </button>
      </form>
    </Modal>
  );
}
