import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, KeyRound, Mail } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { api, jsonBody } from '../../services/api';

export const LoginView: React.FC = () => {
  const { signIn, checkingSession } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // OTP Reset flow state
  const [mode, setMode] = useState<'login' | 'otp-request' | 'otp-verify'>('login');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      await signIn(email.trim(), password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign-in failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRequestOtp = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setInfo('');
    setDevOtp(null);
    setSubmitting(true);
    try {
      const res = await api<{ detail: string; dev_otp?: string }>('/api/auth/request-password-otp', {
        method: 'POST',
        body: jsonBody({ email: email.trim() }),
      });
      setInfo(res.detail);
      if (res.dev_otp) setDevOtp(res.dev_otp);
      setMode('otp-verify');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not send verification code.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyOtp = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setInfo('');
    if (otpCode.length !== 6) {
      setError('Please enter the 6-digit verification code.');
      return;
    }
    if (newPassword.length < 12) {
      setError('New password must contain at least 12 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await api('/api/auth/verify-password-otp', {
        method: 'POST',
        body: jsonBody({
          email: email.trim(),
          otp: otpCode.trim(),
          new_password: newPassword,
        }),
      });
      setInfo('Password reset successfully! Please sign in with your new password.');
      setMode('login');
      setPassword('');
      setOtpCode('');
      setNewPassword('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Verification failed. Code may be invalid or expired.');
    } finally {
      setSubmitting(false);
    }
  };

  if (checkingSession) {
    return (
      <main className="grid min-h-screen place-items-center text-sm text-slate-600">
        Checking your session…
      </main>
    );
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10 bg-slate-50/50">
      <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex items-center gap-3">
          <img
            src="/spit-logo.png"
            alt="SPIT Logo"
            className="h-12 w-12 shrink-0 rounded-full border border-slate-200 bg-white p-1 object-contain shadow-sm"
          />
          <div>
            <p className="text-lg font-bold tracking-tight text-slate-900">SPIT</p>
            <p className="text-xs font-medium text-slate-500">AMS · Attendance Management System</p>
          </div>
        </div>

        <div className="mt-8">
          <p className="text-xs font-bold uppercase tracking-wider text-primary-dark">
            {mode === 'login' ? 'SECURE ACCESS' : 'PASSWORD RECOVERY'}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
            {mode === 'login'
              ? 'Sign in to AMS'
              : mode === 'otp-request'
              ? 'Reset Password via OTP'
              : 'Enter Verification Code'}
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {mode === 'login'
              ? 'Use your institutional account. Role-based permissions are assigned by the server.'
              : mode === 'otp-request'
              ? 'Enter your registered email address to receive a 6-digit one-time verification code.'
              : `A 6-digit verification code was sent to ${email}.`}
          </p>
        </div>

        {error && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">{error}</p>}
        {info && <p role="status" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">{info}</p>}
        {devOtp && (
          <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-xs text-sky-800">
            <span className="font-bold">Development Mode OTP:</span> <span className="font-mono text-sm font-bold text-sky-900">{devOtp}</span>
          </div>
        )}

        {mode === 'login' && (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block text-xs font-semibold text-slate-700">
              Institutional email
              <input
                required
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-700">
              Password
              <input
                required
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
              />
            </label>
            <button
              disabled={submitting}
              type="submit"
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-60"
            >
              {submitting ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} />
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('otp-request');
                setError('');
                setInfo('');
              }}
              className="block w-full text-right text-xs font-medium text-primary hover:underline"
            >
              Forgot password? Reset with OTP
            </button>
          </form>
        )}

        {mode === 'otp-request' && (
          <form onSubmit={handleRequestOtp} className="mt-6 space-y-4">
            <label className="block text-xs font-semibold text-slate-700">
              Your registered email
              <input
                required
                type="email"
                placeholder="name@ams.dev"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
              />
            </label>
            <button
              disabled={submitting || !email.trim()}
              type="submit"
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-60"
            >
              <Mail size={16} />
              {submitting ? 'Sending code…' : 'Send 6-Digit Code'}
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setError('');
                setInfo('');
              }}
              className="block w-full text-center text-xs font-medium text-slate-500 hover:text-slate-800"
            >
              Back to sign in
            </button>
          </form>
        )}

        {mode === 'otp-verify' && (
          <form onSubmit={handleVerifyOtp} className="mt-6 space-y-4">
            <label className="block text-xs font-semibold text-slate-700">
              6-digit verification code
              <input
                required
                maxLength={6}
                pattern="\d{6}"
                placeholder="123456"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-center font-mono text-lg tracking-widest outline-none transition focus:border-primary"
              />
            </label>

            <label className="block text-xs font-semibold text-slate-700">
              New password (min 12 characters)
              <input
                required
                minLength={12}
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
              />
            </label>

            <button
              disabled={submitting || otpCode.length !== 6 || newPassword.length < 12}
              type="submit"
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-60"
            >
              <KeyRound size={16} />
              {submitting ? 'Verifying…' : 'Reset Password & Sign In'}
            </button>

            <div className="flex justify-between text-xs">
              <button
                type="button"
                onClick={handleRequestOtp}
                className="font-medium text-primary hover:underline"
              >
                Resend code
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError('');
                  setInfo('');
                }}
                className="font-medium text-slate-500 hover:text-slate-800"
              >
                Back to sign in
              </button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
};
