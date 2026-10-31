import React, { useState } from 'react';
import * as api from '../api';

const DEMO_USERS = [
  { role: 'Admin', email: 'admin@brightloop.com', pass: 'Admin@123!', label: 'Admin (Full Ops)' },
  { role: 'Staff', email: 'staff@brightloop.com', pass: 'Staff@123!', label: 'Staff (Billing/Subs)' },
  { role: 'Customer', email: 'customer@brightloop.com', pass: 'Cust@1234!', label: 'Customer (Portal)' },
];

function checkPassword(p) {
  return {
    len: p.length >= 8,
    upper: /[A-Z]/.test(p),
    lower: /[a-z]/.test(p),
    special: /[^A-Za-z0-9]/.test(p),
  };
}

export default function AuthScreen({ onLogin, toast }) {
  const [tab, setTab] = useState('signin'); // 'signin' | 'signup' | 'reset'
  const [loading, setLoading] = useState(false);

  // Sign In State
  const [email, setEmail] = useState('admin@brightloop.com');
  const [password, setPassword] = useState('Admin@123!');

  // Sign Up State
  const [name, setName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPass, setRegPass] = useState('');

  // Password Reset State
  const [resetEmail, setResetEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPass, setNewPass] = useState('');
  const [resetStep, setResetStep] = useState(1);

  const regReqs = checkPassword(regPass);
  const isRegValid = Object.values(regReqs).every(Boolean);

  const resetReqs = checkPassword(newPass);
  const isResetValid = Object.values(resetReqs).every(Boolean);

  function handleDemoSelect(u) {
    setEmail(u.email);
    setPassword(u.pass);
    setTab('signin');
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.login(email.trim(), password);
      toast(`Signed in successfully as ${res.user.name}`, 'ok');
      onLogin(res.user);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  async function handleSignUp(e) {
    e.preventDefault();
    if (!isRegValid) {
      toast('Please satisfy all password complexity rules', 'err');
      return;
    }
    setLoading(true);
    try {
      await api.registerCustomer(regEmail.trim(), regPass, name.trim());
      toast('Customer account created. Signing you in…', 'ok');
      const res = await api.login(regEmail.trim(), regPass);
      onLogin(res.user);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  async function handleResetRequest(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.requestReset(resetEmail.trim());
      toast(res.message || 'Reset token generated and logged to console', 'ok');
      if (res.demo_reset_token) {
        setResetToken(res.demo_reset_token);
      }
      setResetStep(2);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  async function handleResetConfirm(e) {
    e.preventDefault();
    if (!isResetValid) {
      toast('Please satisfy all password complexity rules', 'err');
      return;
    }
    setLoading(true);
    try {
      await api.confirmReset(resetToken.trim(), newPass);
      toast('Password reset complete. You can now sign in.', 'ok');
      setEmail(resetEmail);
      setPassword(newPass);
      setTab('signin');
      setResetStep(1);
    } catch (err) {
      toast(err.message, 'err');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#090a0f] flex flex-col items-center justify-center p-4 antialiased selection:bg-zinc-800 selection:text-white">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-6">
          <div className="inline-flex w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-800 items-center justify-center text-zinc-100 font-bold text-sm shadow-md mb-3">
            BL
          </div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">Brightloop Software</h1>
          <p className="text-xs text-zinc-400 mt-1">Enterprise Subscription & Recurring Billing</p>
        </div>

        {/* Quick Demo Credential Pills */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5 px-0.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
              Demo Access Credentials
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {DEMO_USERS.map((u) => {
              const active = email === u.email;
              return (
                <button
                  key={u.role}
                  type="button"
                  onClick={() => handleDemoSelect(u)}
                  className={`py-1.5 px-2 text-xs rounded-lg border transition text-center truncate ${
                    active
                      ? 'bg-white text-zinc-950 font-semibold border-white shadow-sm'
                      : 'bg-zinc-900/80 text-zinc-400 border-zinc-800/80 hover:text-zinc-200 hover:bg-zinc-800/80'
                  }`}
                >
                  {u.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Card */}
        <div className="bg-[#0e1017] border border-zinc-800/90 rounded-2xl p-6 shadow-2xl">
          {/* Sub-tab selection */}
          {tab !== 'reset' && (
            <div className="flex rounded-lg bg-zinc-950/80 p-1 mb-5 border border-zinc-800/80">
              <button
                type="button"
                onClick={() => setTab('signin')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition ${
                  tab === 'signin' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => setTab('signup')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition ${
                  tab === 'signup' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Create Account
              </button>
            </div>
          )}

          {/* SIGN IN */}
          {tab === 'signin' && (
            <form onSubmit={handleSignIn} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Email address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@brightloop.com"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-zinc-300">Password</label>
                  <button
                    type="button"
                    onClick={() => {
                      setResetEmail(email);
                      setTab('reset');
                      setResetStep(1);
                    }}
                    className="text-[11px] text-zinc-400 hover:text-zinc-200 transition underline underline-offset-2"
                  >
                    Forgot password?
                  </button>
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? 'Authenticating…' : 'Sign in to Console'}
              </button>
            </form>
          )}

          {/* SIGN UP */}
          {tab === 'signup' && (
            <form onSubmit={handleSignUp} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Full Name or Company</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Acme Technologies"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Work Email</label>
                <input
                  type="email"
                  required
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="billing@acme.com"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={regPass}
                  onChange={(e) => setRegPass(e.target.value)}
                  placeholder="SecurePassword123!"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition"
                />

                <div className="mt-2.5 p-2 bg-zinc-950 rounded-lg border border-zinc-800/80 grid grid-cols-2 gap-1.5 text-[10px] text-zinc-400">
                  <div className="flex items-center gap-1.5">
                    <span className={regReqs.len ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                    <span>8+ characters</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={regReqs.upper ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                    <span>1 uppercase</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={regReqs.lower ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                    <span>1 lowercase</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={regReqs.special ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                    <span>1 special char</span>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !isRegValid}
                className={`w-full mt-2 py-2.5 text-xs font-semibold rounded-lg shadow-sm transition flex items-center justify-center gap-2 ${
                  isRegValid && !loading
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                    : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                }`}
              >
                {loading ? 'Creating account…' : 'Register Customer Account'}
              </button>
            </form>
          )}

          {/* PASSWORD RESET */}
          {tab === 'reset' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                <span className="text-xs font-semibold text-zinc-200">Reset Account Password</span>
                <button
                  type="button"
                  onClick={() => setTab('signin')}
                  className="text-xs text-zinc-400 hover:text-zinc-200 transition"
                >
                  &larr; Back
                </button>
              </div>

              {resetStep === 1 ? (
                <form onSubmit={handleResetRequest} className="space-y-3.5">
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    Enter your registered email to dispatch a secure one-time password reset token.
                  </p>
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">Account Email</label>
                    <input
                      type="email"
                      required
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                      placeholder="admin@brightloop.com"
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20 transition"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
                  >
                    {loading ? 'Generating…' : 'Generate Reset Token'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleResetConfirm} className="space-y-3.5">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">Reset Token</label>
                    <input
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder="Token from email or server"
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">New Password</label>
                    <input
                      type="password"
                      required
                      value={newPass}
                      onChange={(e) => setNewPass(e.target.value)}
                      placeholder="NewStrongPass123!"
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20"
                    />

                    <div className="mt-2.5 p-2 bg-zinc-950 rounded-lg border border-zinc-800/80 grid grid-cols-2 gap-1.5 text-[10px] text-zinc-400">
                      <div className="flex items-center gap-1.5">
                        <span className={resetReqs.len ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                        <span>8+ characters</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={resetReqs.upper ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                        <span>1 uppercase</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={resetReqs.lower ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                        <span>1 lowercase</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={resetReqs.special ? 'text-emerald-400' : 'text-zinc-600'}>●</span>
                        <span>1 special char</span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !isResetValid}
                    className={`w-full py-2.5 text-xs font-semibold rounded-lg shadow-sm transition ${
                      isResetValid && !loading
                        ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                        : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                    }`}
                  >
                    {loading ? 'Updating…' : 'Update Password & Sign In'}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
