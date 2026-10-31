import React, { useEffect, useState, useCallback } from 'react';
import * as api from '../api';
import { swr, cacheSet } from '../cache';
import NewStaffModal from './modals/NewStaffModal';

export default function Staff({ toast }) {
  const [staff, setStaff] = useState(() => {
    const admins = swr('swr_users_admin', () => null) || [];
    const staffUsers = swr('swr_users_staff', () => null) || [];
    return [...admins, ...staffUsers];
  });
  const [loading, setLoading] = useState(staff.length === 0);
  const [showNew, setShowNew] = useState(false);

  const loadData = useCallback(() => {
    Promise.all([api.getUsers('admin', 100), api.getUsers('staff', 100)])
      .then(([admins, staffUsers]) => {
        setStaff([...admins, ...staffUsers]);
      })
      .catch((err) => toast(err.message, 'err'))
      .finally(() => setLoading(false));
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleStaffCreated(newStaff) {
    if (newStaff) {
      setStaff((prev) => [newStaff, ...prev]);
      const currentStaff = swr('swr_users_staff', () => null) || [];
      cacheSet('swr_users_staff', [newStaff, ...currentStaff]);
    }
    setShowNew(false);
    loadData();
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 antialiased">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">Staff & Administrative Directory</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Internal operators with role-based access control (Admin & Staff) &bull; Only Admins can provision new staff
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-white hover:bg-zinc-200 text-zinc-950 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5 self-start sm:self-auto"
        >
          <span>+</span> Provision Staff Member
        </button>
      </div>

      {/* Table */}
      <div className="bg-[#0e1017] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400">
                <th className="text-left px-4 py-3.5 font-medium">Name</th>
                <th className="text-left px-4 py-3.5 font-medium">Email</th>
                <th className="text-left px-4 py-3.5 font-medium">System Role</th>
                <th className="text-left px-4 py-3.5 font-medium">Assigned Access & Scope</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {loading && staff.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-zinc-400">
                    <span className="inline-block w-4 h-4 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin mr-2"></span>
                    Loading directory…
                  </td>
                </tr>
              ) : staff.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-zinc-400">
                    No administrative staff members found.
                  </td>
                </tr>
              ) : (
                staff.map((m) => (
                  <tr key={m.id} className="hover:bg-zinc-800/30 transition">
                    <td className="px-4 py-3.5 font-semibold text-zinc-100">{m.name}</td>
                    <td className="px-4 py-3.5 font-mono text-zinc-300">{m.email}</td>
                    <td className="px-4 py-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                          m.role === 'admin'
                            ? 'bg-zinc-800 text-zinc-200 border-zinc-700'
                            : 'bg-zinc-900 text-zinc-400 border-zinc-800'
                        }`}
                      >
                        {m.role}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-zinc-400 text-[11px]">
                      {m.role === 'admin'
                        ? 'Full root control: Tax rules, Discount engine, Staff provisioning & Audit logs'
                        : 'Day-to-day operations: Quotations, Subscriptions pipeline, Bulk billing & Payments'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showNew && (
        <NewStaffModal
          onClose={() => setShowNew(false)}
          onSaved={handleStaffCreated}
          toast={toast}
        />
      )}
    </div>
  );
}
