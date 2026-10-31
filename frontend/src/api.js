import { cache } from './cache';

const API_URL = import.meta.env.VITE_API_URL || '';
const BASE = API_URL ? `${API_URL.replace(/\/+$/, '')}/api/v1` : '/api/v1';
let _token = localStorage.getItem('bl_token') || '';

export function setToken(t) {
  _token = t || '';
  if (t) localStorage.setItem('bl_token', t);
  else {
    localStorage.removeItem('bl_token');
    cache.clear();
  }
}

export function getToken() {
  return _token;
}

export async function req(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...opts.headers };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

export async function download(path, filename) {
  const headers = {};
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  const res = await fetch(`${BASE}${path}`, { headers });
  if (!res.ok) throw new Error(`Download failed: HTTP ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function items(res) {
  if (!res) return [];
  if (Array.isArray(res)) return res;
  if (Array.isArray(res.items)) return res.items;
  return [];
}

// ─── SWR Helper ─────────────────────────────────────────────────────────────
// Returns cached data immediately (0ms). If callback provided, revalidates in background.
export async function swr(cacheKey, fetchFn, onFresh = null) {
  const cached = cache.get(cacheKey);
  const bgFetch = fetchFn()
    .then((fresh) => {
      cache.set(cacheKey, fresh);
      if (onFresh) onFresh(fresh);
      return fresh;
    })
    .catch((err) => {
      // If we don't even have cached data, rethrow
      if (!cached) throw err;
      return cached;
    });

  if (cached) {
    return { data: cached, isStale: true, refresh: bgFetch };
  }
  const fresh = await bgFetch;
  return { data: fresh, isStale: false, refresh: Promise.resolve(fresh) };
}

// ─── Auth ──────────────────────────────────────────────────────────────────

export async function login(email, password) {
  const data = await req('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function register(name, email, password) {
  const data = await req('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function registerCustomer(email, password, name) {
  return register(name, email, password);
}

export async function getMe() {
  return req('/auth/me');
}

export async function requestReset(email) {
  return req('/auth/reset-password/request', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function confirmReset(token, new_password) {
  return req('/auth/reset-password/confirm', {
    method: 'POST',
    body: JSON.stringify({ token, new_password }),
  });
}

// ─── Dashboard ─────────────────────────────────────────────────────────────

export async function getDashboardStats(onFresh = null) {
  return swr('dashboard_stats', () => req('/dashboard/stats'), onFresh);
}

// ─── Products & Plans ──────────────────────────────────────────────────────

export async function getProducts(page = 1, size = 100, onFresh = null) {
  const key = `products_${page}_${size}`;
  return swr(
    key,
    async () => {
      const res = await req(`/products?page=${page}&page_size=${size}`);
      return { items: items(res), total: res.total || 0 };
    },
    onFresh
  );
}

export async function createProduct(body) {
  const res = await req('/products', { method: 'POST', body: JSON.stringify(body) });
  cache.clear('products');
  return res;
}

export async function createVariant(productId, body) {
  const res = await req(`/products/${productId}/variants`, { method: 'POST', body: JSON.stringify(body) });
  cache.clear('products');
  return res;
}

export async function getPlans(page = 1, size = 100, onFresh = null) {
  const key = `plans_${page}_${size}`;
  return swr(
    key,
    async () => {
      const res = await req(`/plans?page=${page}&page_size=${size}`);
      return { items: items(res), total: res.total || 0 };
    },
    onFresh
  );
}

export async function createPlan(body) {
  const res = await req('/plans', { method: 'POST', body: JSON.stringify(body) });
  cache.clear('plans');
  return res;
}

export async function getTaxes(onFresh = null) {
  return swr('taxes', async () => items(await req('/taxes')), onFresh);
}

export async function getDiscounts(onFresh = null) {
  return swr('discounts', async () => items(await req('/discounts')), onFresh);
}

export async function createDiscount(body) {
  const res = await req('/discounts', { method: 'POST', body: JSON.stringify(body) });
  cache.clear('discounts');
  return res;
}

// ─── Subscriptions ─────────────────────────────────────────────────────────

export async function getSubscriptions({ page = 1, size = 25, status = '', search = '' } = {}, onFresh = null) {
  let url = `/subscriptions?page=${page}&page_size=${size}`;
  if (status && status !== 'all') url += `&status=${status}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  const key = `subs_${page}_${size}_${status}_${search}`;

  return swr(
    key,
    async () => {
      const res = await req(url);
      return { items: items(res), total: res.total || 0, pages: res.pages || 1 };
    },
    onFresh
  );
}

export async function createSubscription(body) {
  const res = await req('/subscriptions', { method: 'POST', body: JSON.stringify(body) });
  cache.clear('subs');
  cache.clear('portal');
  cache.clear('dashboard');
  return res;
}

export async function updateSubStatus(id, status) {
  const res = await req(`/subscriptions/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
  cache.clear('subs');
  cache.clear('portal');
  cache.clear('dashboard');
  return res;
}

// ─── Invoices ──────────────────────────────────────────────────────────────

export async function getInvoices({ page = 1, size = 25, status = '', overdue = false } = {}, onFresh = null) {
  let url = `/invoices?page=${page}&page_size=${size}`;
  if (status && status !== 'all') url += `&status=${status}`;
  if (overdue) url += `&is_overdue=true`;
  const key = `invs_${page}_${size}_${status}_${overdue}`;

  return swr(
    key,
    async () => {
      const res = await req(url);
      return { items: items(res), total: res.total || 0, pages: res.pages || 1 };
    },
    onFresh
  );
}

export async function getInvoice(id) {
  return req(`/invoices/${id}`);
}

export async function generateInvoice(subscriptionId) {
  const res = await req(`/invoices/generate/${subscriptionId}`, { method: 'POST' });
  cache.clear('invs');
  cache.clear('subs');
  cache.clear('portal');
  cache.clear('dashboard');
  return res;
}

export async function generateBulk() {
  const res = await req('/invoices/generate-bulk', { method: 'POST' });
  cache.clear('invs');
  cache.clear('subs');
  cache.clear('portal');
  cache.clear('dashboard');
  return res;
}

export async function confirmInvoice(id) {
  const res = await req(`/invoices/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'confirmed' }),
  });
  cache.clear('invs');
  cache.clear('portal');
  return res;
}

export async function sendInvoiceEmail(id) {
  return req(`/invoices/${id}/send`, { method: 'POST' });
}

export async function downloadPdf(id, number = 'INV') {
  return download(`/invoices/${id}/pdf`, `${number}.pdf`);
}

// ─── Payments ──────────────────────────────────────────────────────────────

export async function recordPayment(body) {
  const res = await req('/payments', { method: 'POST', body: JSON.stringify(body) });
  cache.clear('invs');
  cache.clear('portal');
  cache.clear('dashboard');
  return res;
}

// ─── Users / Staff ─────────────────────────────────────────────────────────

export async function getUsers(role = '', size = 100, onFresh = null) {
  let url = `/auth/users?page_size=${size}`;
  if (role) url += `&role=${role}`;
  const key = `users_${role}_${size}`;
  return swr(key, async () => items(await req(url)), onFresh);
}

export async function createStaff(body) {
  const res = await req('/auth/staff', { method: 'POST', body: JSON.stringify(body) });
  cache.clear('users');
  return res;
}

// ─── Customer Portal ───────────────────────────────────────────────────────

export async function getPortalStats(onFresh = null) {
  return swr('portal_stats', () => req('/portal/stats'), onFresh);
}

export async function getPortalSubscriptions(onFresh = null) {
  return swr('portal_subs', async () => items(await req('/portal/subscriptions')), onFresh);
}

export async function getPortalInvoices(onFresh = null) {
  return swr('portal_invs', async () => items(await req('/portal/invoices')), onFresh);
}

// ─── Exports ───────────────────────────────────────────────────────────────

export async function exportSubscriptions() {
  const d = new Date().toISOString().slice(0, 10);
  return download('/export/subscriptions', `subscriptions_${d}.csv`);
}

export async function exportInvoices() {
  const d = new Date().toISOString().slice(0, 10);
  return download('/export/invoices', `invoices_${d}.csv`);
}
