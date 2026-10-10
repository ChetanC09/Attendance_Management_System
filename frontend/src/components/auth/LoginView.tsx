import React, { useState } from 'react';
import { ArrowRight, GraduationCap } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { api, jsonBody } from '../../services/api';
export const LoginView: React.FC = () => {
  const { signIn, checkingSession } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const resetQuery = new URLSearchParams(window.location.search);
  const initialResetToken = resetQuery.get('token') || resetQuery.get('reset_token') || '';
  const [mode, setMode] = useState<'login' | 'forgot' | 'reset'>(initialResetToken ? 'reset' : 'login');
  const [resetToken, setResetToken] = useState(initialResetToken);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setSubmitting(true);
    try { await signIn(email.trim(), password); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Sign-in failed.'); }
    finally { setSubmitting(false); }
  };

  const passwordAction = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setSubmitting(true);
    try {
      if (mode === 'forgot') {
        await api('/api/auth/forgot-password', { method: 'POST', body: jsonBody({ email: email.trim() }) });
        setError('If the account exists, password reset instructions have been sent.');
      } else {
        await api<void>('/api/auth/reset-password', { method: 'POST', body: jsonBody({ token: resetToken.trim(), new_password: password }) });
        setMode('login'); setPassword(''); setResetToken(''); window.history.replaceState({}, '', window.location.pathname);
        setError('Password reset. Sign in with your new password.');
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Password request failed.'); }
    finally { setSubmitting(false); }
  };

  if (checkingSession) return <main className="grid min-h-screen place-items-center text-sm text-slate-600">Checking your session…</main>;

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
        <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-white"><GraduationCap size={21} /></span><div><p className="text-sm font-semibold text-slate-900">SPIT Attendance</p><p className="text-xs text-slate-500">Attendance Management System</p></div></div>
        <div className="mt-8"><p className="text-xs font-medium text-primary-dark">SECURE ACCESS</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Sign in to AMS</h1><p className="mt-2 text-sm leading-6 text-slate-600">Use your institutional account. Your permissions are assigned by the server.</p></div>
        {mode === 'login' ? <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm font-medium text-slate-800">Institutional email<input required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary" /></label>
          <label className="block text-sm font-medium text-slate-800">Password<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary" /></label>
          {error && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm text-rose-800">{error}</p>}
          <button disabled={submitting} type="submit" className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60">{submitting ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} /></button>
          <button type="button" onClick={() => { setMode('forgot'); setError(''); }} className="block w-full text-right text-xs font-medium text-primary-dark">Forgot password?</button>
        </form> : <form onSubmit={passwordAction} className="mt-6 space-y-4">
          {mode === 'forgot' ? <label className="block text-sm font-medium text-slate-800">Institutional email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label> : <><label className="block text-sm font-medium text-slate-800">Reset token<input required minLength={20} value={resetToken} onChange={(event) => setResetToken(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label><label className="block text-sm font-medium text-slate-800">New password<input required minLength={12} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label></>}
          {error && <p role="status" className="rounded-lg bg-stone-50 px-3 py-2.5 text-sm text-slate-700">{error}</p>}
          <button disabled={submitting} className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white disabled:opacity-60">{submitting ? 'Please wait…' : mode === 'forgot' ? 'Send reset instructions' : 'Reset password'}</button>
          <button type="button" onClick={() => { setMode('login'); setError(''); }} className="block w-full text-xs font-medium text-primary-dark">Back to sign in</button>
        </form>}
      </section>
    </main>
  );
};
