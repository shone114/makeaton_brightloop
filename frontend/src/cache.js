// In-memory + sessionStorage client-side fast cache for instant 0ms loads
const memCache = new Map();

export const cache = {
  get(key) {
    if (memCache.has(key)) return memCache.get(key);
    try {
      const raw = sessionStorage.getItem(`bl_c_${key}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        memCache.set(key, parsed);
        return parsed;
      }
    } catch (_) {}
    return null;
  },

  set(key, data) {
    memCache.set(key, data);
    try {
      sessionStorage.setItem(`bl_c_${key}`, JSON.stringify(data));
    } catch (_) {}
  },

  update(key, updater) {
    const cur = cache.get(key);
    if (cur !== null) {
      const next = updater(cur);
      cache.set(key, next);
      return next;
    }
    return null;
  },

  clear(pattern = '') {
    if (!pattern) {
      memCache.clear();
      try {
        Object.keys(sessionStorage).forEach((k) => {
          if (k.startsWith('bl_c_')) sessionStorage.removeItem(k);
        });
      } catch (_) {}
      return;
    }
    for (const k of memCache.keys()) {
      if (k.includes(pattern)) memCache.delete(k);
    }
    try {
      Object.keys(sessionStorage).forEach((k) => {
        if (k.startsWith('bl_c_') && k.includes(pattern)) sessionStorage.removeItem(k);
      });
    } catch (_) {}
  },
};

export function swr(key) {
  return cache.get(key);
}

export function cacheGet(key) {
  return cache.get(key);
}

export function cacheSet(key, data) {
  return cache.set(key, data);
}
