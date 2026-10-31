import React, { useEffect } from 'react';

export default function Modal({ title, onClose, children }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-[#0e1017] border border-zinc-800/90 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-scale-up"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/80 bg-zinc-950/60">
          <h3 className="text-sm font-semibold text-zinc-100 tracking-tight">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 transition text-lg leading-none p-1 rounded-md hover:bg-zinc-800/60"
          >
            &times;
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export function Field({ label, children }) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-zinc-300">{label}</label>
      {children}
    </div>
  );
}

export const inputCls =
  'w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition';

export const selectCls =
  'w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition font-medium';
