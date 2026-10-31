import React, { useState } from 'react';
import * as api from '../../api';
import Modal, { Field, inputCls } from './Modal';

function checkPassword(p) {
  return {
    len: p.length >= 8,
    upper: /[A-Z]/.test(p),
    lower: /[a-z]/.test(p),
    special: /[^A-Za-z0-9]/.test(p),
  };
}

function Check({ ok }) {
  return <span className={ok ? 'text-emerald-400 font-bold mr-1' : 'text-zinc-600 mr-1'}>●</span>;
}

export default function NewStaffModal({ onClose, onSaved, toast }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const s = checkPassword(password);
  const valid = Object.values(s).every(Boolean);

  async function submit(e) {
    e.preventDefault();
    if (!valid) {
      toast('Please satisfy password security rules', 'err');
      return;
    }
    setLoading(true);
    const optimisticStaff = {
      id: 'temp-' + Date.now(),
      name: name.trim(),
      email: email.trim(),
      role: 'staff',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    try {
      const res = await api.createStaff(email.trim(), password, name.trim());
      toast(`Staff member ${name} provisioned successfully`, 'ok');
      onSaved(res || optimisticStaff);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Provision Staff Member" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Full Name">
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Jane Smith"
            className={inputCls}
          />
        </Field>
        <Field label="Staff Email Address">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="jane@brightloop.com"
            className={inputCls}
          />
        </Field>
        <Field label="Temporary Password">
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="SecureStaff123!"
            className={inputCls}
          />
          <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-zinc-400 p-2 bg-zinc-950 rounded-lg border border-zinc-800">
            <span><Check ok={s.len} /> 8+ characters</span>
            <span><Check ok={s.upper} /> Uppercase</span>
            <span><Check ok={s.lower} /> Lowercase</span>
            <span><Check ok={s.special} /> Special character</span>
          </div>
        </Field>
        <button
          type="submit"
          disabled={loading || !valid}
          className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-40"
        >
          {loading ? 'Provisioning…' : 'Create Staff Account'}
        </button>
      </form>
    </Modal>
  );
}
