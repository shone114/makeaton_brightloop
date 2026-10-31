import React, { useEffect, useState, useCallback } from 'react';
import * as api from '../api';
import { swr, cacheSet } from '../cache';
import NewProductModal from './modals/NewProductModal';
import NewPlanModal from './modals/NewPlanModal';
import NewDiscountModal from './modals/NewDiscountModal';

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Products({ user, toast }) {
  const [products, setProducts] = useState(() => swr('swr_products_1_100', () => null)?.items || []);
  const [plans, setPlans] = useState(() => swr('swr_plans_1_100', () => null)?.items || []);
  const [discounts, setDiscounts] = useState(() => swr('swr_discounts', () => null) || []);
  const [loading, setLoading] = useState(!products.length && !plans.length);
  const [tab, setTab] = useState('products');

  // Modals
  const [showProd, setShowProd] = useState(false);
  const [showPlan, setShowPlan] = useState(false);
  const [showDisc, setShowDisc] = useState(false);

  const role = user?.role;

  const loadData = useCallback(async () => {
    try {
      const [p, pl, d] = await Promise.all([
        api.getProducts(1, 100),
        api.getPlans(1, 100),
        api.getDiscounts(),
      ]);
      setProducts(p.items || []);
      setPlans(pl.items || []);
      setDiscounts(d || []);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleProductCreated(newP) {
    if (newP) {
      setProducts((prev) => [newP, ...prev]);
      cacheSet('swr_products_1_100', { items: [newP, ...products], total: products.length + 1 });
    }
    setShowProd(false);
    loadData();
  }

  function handlePlanCreated(newPl) {
    if (newPl) {
      setPlans((prev) => [newPl, ...prev]);
      cacheSet('swr_plans_1_100', { items: [newPl, ...plans], total: plans.length + 1 });
    }
    setShowPlan(false);
    loadData();
  }

  function handleDiscountCreated(newD) {
    if (newD) {
      setDiscounts((prev) => [newD, ...prev]);
      cacheSet('swr_discounts', [newD, ...discounts]);
    }
    setShowDisc(false);
    loadData();
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 antialiased">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">Product Catalog, Plans & Discount Engine</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Configure software products, multi-attribute variants, recurring billing plans & automated discount rules
          </p>
        </div>

        {role === 'admin' && (
          <div className="flex items-center gap-2">
            {tab === 'products' && (
              <button
                onClick={() => setShowProd(true)}
                className="px-3.5 py-2 bg-white hover:bg-zinc-200 text-zinc-950 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
              >
                <span>+</span> Add Product & Variant
              </button>
            )}
            {tab === 'plans' && (
              <button
                onClick={() => setShowPlan(true)}
                className="px-3.5 py-2 bg-white hover:bg-zinc-200 text-zinc-950 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
              >
                <span>+</span> Configure Plan
              </button>
            )}
            {tab === 'discounts' && (
              <button
                onClick={() => setShowDisc(true)}
                className="px-3.5 py-2 bg-white hover:bg-zinc-200 text-zinc-950 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
              >
                <span>+</span> Add Discount Rule
              </button>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5">
        {[
          { id: 'products', label: `Products (${products.length})` },
          { id: 'plans', label: `Billing Plans (${plans.length})` },
          { id: 'discounts', label: `Discount Rules (${discounts.length})` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
              tab === t.id
                ? 'bg-white text-zinc-950 shadow-sm'
                : 'bg-zinc-900/80 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-zinc-800/80'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && products.length === 0 ? (
        <div className="p-8 text-center text-zinc-400 text-xs">
          <span className="inline-block w-4 h-4 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin mr-2"></span>
          Loading catalog configurations…
        </div>
      ) : (
        <>
          {/* PRODUCTS TAB */}
          {tab === 'products' && (
            <div className="bg-[#0e1017] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400">
                      <th className="text-left px-4 py-3.5 font-medium">Product Name & Notes</th>
                      <th className="text-left px-4 py-3.5 font-medium">Type</th>
                      <th className="text-right px-4 py-3.5 font-medium">Sales Price</th>
                      <th className="text-right px-4 py-3.5 font-medium">Cost Price</th>
                      <th className="text-left px-4 py-3.5 font-medium">Variants & Price Extras</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {products.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center text-zinc-400">
                          No products configured in catalog.
                        </td>
                      </tr>
                    ) : (
                      products.map((p) => (
                        <tr key={p.id} className="hover:bg-zinc-800/30 transition">
                          <td className="px-4 py-3.5">
                            <span className="font-semibold text-zinc-100">{p.name}</span>
                            {p.notes && <p className="text-[11px] text-zinc-400 mt-0.5">{p.notes}</p>}
                          </td>
                          <td className="px-4 py-3.5">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-zinc-900 border border-zinc-800 text-zinc-300">
                              {p.type}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-right font-mono font-semibold text-emerald-400 tabular-nums">
                            ${fmt(p.sales_price)}
                          </td>
                          <td className="px-4 py-3.5 text-right font-mono text-zinc-400 tabular-nums">
                            ${fmt(p.cost_price)}
                          </td>
                          <td className="px-4 py-3.5">
                            {(p.variants || []).length === 0 ? (
                              <span className="text-zinc-500 text-[11px]">Base edition only</span>
                            ) : (
                              <div className="flex flex-wrap gap-1.5">
                                {(p.variants || []).map((v) => (
                                  <span
                                    key={v.id}
                                    className="px-2 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[11px] text-zinc-300 font-medium"
                                  >
                                    {v.attribute_name}: <strong className="text-zinc-100">{v.attribute_value}</strong> (+${fmt(v.price_extra)})
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* PLANS TAB */}
          {tab === 'plans' && (
            <div className="bg-[#0e1017] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400">
                      <th className="text-left px-4 py-3.5 font-medium">Plan Name</th>
                      <th className="text-left px-4 py-3.5 font-medium">Billing Period</th>
                      <th className="text-right px-4 py-3.5 font-medium">Recurring Price</th>
                      <th className="text-left px-4 py-3.5 font-medium">Min Quantity</th>
                      <th className="text-left px-4 py-3.5 font-medium">Lifecycle Capabilities</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {plans.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center text-zinc-400">
                          No plans configured yet.
                        </td>
                      </tr>
                    ) : (
                      plans.map((pl) => (
                        <tr key={pl.id} className="hover:bg-zinc-800/30 transition">
                          <td className="px-4 py-3.5 font-semibold text-zinc-100">{pl.name}</td>
                          <td className="px-4 py-3.5 capitalize font-medium text-zinc-300">{pl.billing_period}</td>
                          <td className="px-4 py-3.5 text-right font-mono font-semibold text-zinc-100 tabular-nums">
                            ${fmt(pl.amount)}
                          </td>
                          <td className="px-4 py-3.5 font-mono text-zinc-300">{pl.min_quantity || 1} unit</td>
                          <td className="px-4 py-3.5">
                            <div className="flex flex-wrap gap-1">
                              {pl.is_pausable && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-300 font-medium">
                                  Pausable
                                </span>
                              )}
                              {pl.is_closable_early && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-300 font-medium">
                                  Early Close
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* DISCOUNTS TAB */}
          {tab === 'discounts' && (
            <div className="bg-[#0e1017] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400">
                      <th className="text-left px-4 py-3.5 font-medium">Discount Rule</th>
                      <th className="text-left px-4 py-3.5 font-medium">Type</th>
                      <th className="text-right px-4 py-3.5 font-medium">Discount Value</th>
                      <th className="text-right px-4 py-3.5 font-medium">Min Spend ($)</th>
                      <th className="text-left px-4 py-3.5 font-medium">Validity Window</th>
                      <th className="text-right px-4 py-3.5 font-medium">Usage Counter</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {discounts.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="px-4 py-8 text-center text-zinc-400">
                          No discount rules configured.
                        </td>
                      </tr>
                    ) : (
                      discounts.map((d) => (
                        <tr key={d.id} className="hover:bg-zinc-800/30 transition">
                          <td className="px-4 py-3.5 font-semibold text-zinc-100">{d.name}</td>
                          <td className="px-4 py-3.5 capitalize text-zinc-300">
                            {d.type || d.discount_type}
                          </td>
                          <td className="px-4 py-3.5 text-right font-mono font-semibold text-emerald-400 tabular-nums">
                            {(d.type || d.discount_type) === 'percentage' ? `${d.value}%` : `$${fmt(d.value)}`}
                          </td>
                          <td className="px-4 py-3.5 text-right font-mono text-zinc-400 tabular-nums">
                            ${fmt(d.min_amount || d.min_purchase_amount || 0)}
                          </td>
                          <td className="px-4 py-3.5 text-zinc-300 font-mono text-[11px]">
                            {d.start_date ? String(d.start_date).slice(0, 10) : '—'} &rarr;{' '}
                            {d.end_date ? String(d.end_date).slice(0, 10) : '—'}
                          </td>
                          <td className="px-4 py-3.5 text-right font-mono text-zinc-300">
                            {d.used_count ?? d.current_usage ?? 0} / {d.usage_limit || '∞'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      {showProd && (
        <NewProductModal
          onClose={() => setShowProd(false)}
          onSaved={handleProductCreated}
          toast={toast}
        />
      )}
      {showPlan && (
        <NewPlanModal
          products={products}
          onClose={() => setShowPlan(false)}
          onSaved={handlePlanCreated}
          toast={toast}
        />
      )}
      {showDisc && (
        <NewDiscountModal
          products={products}
          onClose={() => setShowDisc(false)}
          onSaved={handleDiscountCreated}
          toast={toast}
        />
      )}
    </div>
  );
}
