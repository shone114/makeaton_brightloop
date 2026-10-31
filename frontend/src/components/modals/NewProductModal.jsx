import React, { useState } from 'react';
import * as api from '../../api';
import Modal, { Field, inputCls, selectCls } from './Modal';

export default function NewProductModal({ onClose, onSaved, toast }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('service');
  const [salesPrice, setSalesPrice] = useState('100.00');
  const [costPrice, setCostPrice] = useState('0.00');
  const [notes, setNotes] = useState('');

  // Variant fields (optional)
  const [variantName, setVariantName] = useState('');
  const [variantValue, setVariantValue] = useState('');
  const [variantExtra, setVariantExtra] = useState('0.00');

  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    const variants = variantName && variantValue ? [
      {
        attribute_name: variantName.trim(),
        attribute_value: variantValue.trim(),
        price_extra: parseFloat(variantExtra || 0),
      }
    ] : [];

    const payload = {
      name: name.trim(),
      type,
      sales_price: parseFloat(salesPrice),
      cost_price: parseFloat(costPrice || 0),
      notes: notes.trim() || null,
      variants,
    };

    const optimisticProduct = {
      id: 'temp-' + Date.now(),
      ...payload,
      created_at: new Date().toISOString(),
    };

    try {
      const res = await api.createProduct(payload);
      toast(`Product "${name}" created`, 'ok');
      onSaved(res || optimisticProduct);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Create Catalog Product" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Product Name">
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Cloud Hosting Seat"
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Product Type">
            <select value={type} onChange={(e) => setType(e.target.value)} className={selectCls}>
              <option value="service">Service</option>
              <option value="consumable">Consumable</option>
              <option value="storable">Storable</option>
            </select>
          </Field>
          <Field label="Sales Price ($)">
            <input
              type="number"
              step="0.01"
              required
              value={salesPrice}
              onChange={(e) => setSalesPrice(e.target.value)}
              placeholder="100.00"
              className={inputCls}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Cost Price ($)">
            <input
              type="number"
              step="0.01"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
              placeholder="0.00"
              className={inputCls}
            />
          </Field>
          <Field label="Notes (optional)">
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Internal spec or notes"
              className={inputCls}
            />
          </Field>
        </div>

        <div className="border-t border-zinc-800/80 pt-3">
          <p className="text-xs text-zinc-400 mb-2 font-medium">Add Variant (optional)</p>
          <div className="grid grid-cols-3 gap-2">
            <Field label="Attribute">
              <input
                type="text"
                value={variantName}
                onChange={(e) => setVariantName(e.target.value)}
                placeholder="Tier"
                className={inputCls}
              />
            </Field>
            <Field label="Value">
              <input
                type="text"
                value={variantValue}
                onChange={(e) => setVariantValue(e.target.value)}
                placeholder="Enterprise"
                className={inputCls}
              />
            </Field>
            <Field label="Extra ($)">
              <input
                type="number"
                step="0.01"
                value={variantExtra}
                onChange={(e) => setVariantExtra(e.target.value)}
                placeholder="50"
                className={inputCls}
              />
            </Field>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-40"
        >
          {loading ? 'Saving…' : 'Create Product'}
        </button>
      </form>
    </Modal>
  );
}
