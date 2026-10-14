import React, { useEffect, useState } from 'react';
import { Download, FileText, KeyRound, Mail, ShieldCheck } from 'lucide-react';
import { api, apiBaseUrl, jsonBody, type ApiUser } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Preference = { channel: string; enabled: boolean };
type FaceProfile = { enrolled: boolean; consented_at: string | null; revoked_at: string | null };

const field =
  'mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-primary';

export const AccountSettingsView: React.FC = () => {
  const { currentUser, currentRole, signOut, addToast } = useApp();
  const [me, setMe] = useState<ApiUser | null>(null);
  const [prefs, setPrefs] = useState<Preference[]>([]);
  const [faceProfile, setFaceProfile] = useState<FaceProfile | null>(null);

  // OTP password change state
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);

  // Face enrollment state
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);

  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<ApiUser>('/api/auth/me').then(setMe);
    api<Preference[]>('/api/notifications/preferences')
      .then(setPrefs)
      .catch(() => setPrefs([]));
    if (currentRole === 'student') {
      api<FaceProfile>('/api/student/face-profile')
        .then(setFaceProfile)
        .catch(() => setFaceProfile(null));
    }
  }, [currentRole]);

  const requestOtp = async () => {
    setError('');
    setMessage('');
    setBusy(true);
    setDevOtpHint(null);
    try {
      const email = me?.email || currentUser.email;
      const res = await api<{ detail: string; dev_otp?: string }>(
        '/api/auth/request-password-otp',
        {
          method: 'POST',
          body: jsonBody({ email }),
        }
      );
      setOtpSent(true);
      setMessage(res.detail);
      if (res.dev_otp) {
        setDevOtpHint(res.dev_otp);
      }
      addToast({ type: 'info', message: 'Verification code sent to your email.' });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not send verification code.');
    } finally {
      setBusy(false);
    }
  };

  const verifyAndChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');

    if (otpCode.trim().length !== 6) {
      setError('Please enter the 6-digit verification code.');
      return;
    }
    if (newPassword.length < 12) {
      setError('New password must contain at least 12 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('The passwords you entered do not match.');
      return;
    }

    setBusy(true);
    try {
      const email = me?.email || currentUser.email;
      await api('/api/auth/verify-password-otp', {
        method: 'POST',
        body: jsonBody({
          email,
          otp: otpCode.trim(),
          new_password: newPassword,
        }),
      });
      setMessage('Password updated successfully. Signing out…');
      addToast({ type: 'success', message: 'Password updated. Please sign in with your new password.' });
      setTimeout(() => void signOut(), 1500);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Failed to verify code or update password.');
    } finally {
      setBusy(false);
    }
  };

  const setPreference = async (channel: string, enabled: boolean) => {
    setError('');
    try {
      await api(`/api/notifications/preferences/${channel}?enabled=${enabled}`, { method: 'PUT' });
      setPrefs((old) => [...old.filter((item) => item.channel !== channel), { channel, enabled }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Preference could not be saved.');
    }
  };

  const enrollFace = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');
    if (!consent || !faceFile) {
      setError('Explicit consent and one image are required.');
      return;
    }
    setBusy(true);
    const form = new FormData();
    form.append('consent', 'true');
    form.append('image', faceFile);
    try {
      await api('/api/student/face-profile/enroll', { method: 'POST', body: form });
      setFaceProfile(await api<FaceProfile>('/api/student/face-profile'));
      setMessage('Face profile enrolled successfully. The server stores only the derived embedding.');
      setFaceFile(null);
      setConsent(false);
      addToast({ type: 'success', message: 'Face profile enrolled.' });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Enrollment failed. Check image clarity and lighting.');
    } finally {
      setBusy(false);
    }
  };

  const revokeFace = async () => {
    setError('');
    setMessage('');
    setBusy(true);
    try {
      await api<void>('/api/student/face-profile', { method: 'DELETE' });
      setFaceProfile(await api<FaceProfile>('/api/student/face-profile'));
      setMessage('Face profile consent revoked and profile disabled.');
      addToast({ type: 'info', message: 'Face profile revoked.' });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not revoke face enrollment.');
    } finally {
      setBusy(false);
    }
  };

  const downloadMyTranscriptPdf = () => {
    window.open(`${apiBaseUrl}/api/student/analytics/report/pdf`, '_blank');
  };

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Account · Live Settings</p>
          <h1 className="text-2xl font-semibold text-slate-900">Profile & Settings</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage account credentials, face attendance enrollment, and preferences.
          </p>
        </div>

        {currentRole === 'student' && (
          <button
            type="button"
            onClick={downloadMyTranscriptPdf}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            <Download size={14} className="text-slate-500" />
            Download Attendance Statement (PDF)
          </button>
        )}
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {message && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}

      {/* Account Info */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Account details</h2>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          {[
            ['Name', me?.full_name || currentUser.name],
            ['Email', me?.email || currentUser.email],
            ['Institutional ID', me?.institutional_id || currentUser.rollOrEmpId],
            ['Role', me?.role || currentRole.toUpperCase()],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl bg-slate-50/70 p-3">
              <dt className="text-xs font-medium text-slate-500">{label}</dt>
              <dd className="mt-1 text-sm font-semibold text-slate-800">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* Notification Preferences */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Notification preferences</h2>
        <p className="mt-1 text-xs text-slate-500">Choose delivery channels for attendance alerts and approvals.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          {['IN_APP', 'EMAIL', 'SMS'].map((channel) => {
            const item = prefs.find((preference) => preference.channel === channel);
            return (
              <label
                key={channel}
                className="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={item?.enabled || false}
                  onChange={(event) => void setPreference(channel, event.target.checked)}
                  className="rounded border-slate-300 text-primary"
                />
                {channel.replace('_', ' ')}
              </label>
            );
          })}
        </div>
      </section>

      {/* Face Enrollment (Students Only) */}
      {currentRole === 'student' && (
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Face attendance enrollment</h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Enrollment enables quick self check-in using your device camera. The system extracts a mathematical vector representation; your original image is not stored.
            </p>
            <p role="status" className="mt-2 text-xs font-medium text-slate-700">
              Status:{' '}
              {faceProfile ? (
                faceProfile.enrolled ? (
                  <span className="font-semibold text-emerald-700">
                    Active{faceProfile.consented_at ? ` (enrolled ${new Date(faceProfile.consented_at).toLocaleDateString()})` : ''}
                  </span>
                ) : faceProfile.revoked_at ? (
                  <span className="font-semibold text-amber-700">
                    Revoked on {new Date(faceProfile.revoked_at).toLocaleDateString()}
                  </span>
                ) : (
                  <span className="text-slate-500">Not enrolled</span>
                )
              ) : (
                'Checking…'
              )}
            </p>
          </div>

          <form onSubmit={enrollFace} className="space-y-3">
            <label className="block text-xs font-medium text-slate-700">
              Photo of your face (clear lighting, neutral expression, JPEG or PNG)
              <input
                required
                type="file"
                accept="image/jpeg,image/png"
                onChange={(event) => setFaceFile(event.target.files?.[0] || null)}
                className="mt-1.5 block w-full text-xs text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-slate-700 hover:file:bg-slate-200"
              />
            </label>

            <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
              <input
                required
                type="checkbox"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-primary"
              />
              I explicitly consent to processing my face image to generate an attendance verification profile.
            </label>

            <div className="flex flex-wrap gap-2 pt-1">
              <button
                disabled={busy || !faceFile || !consent}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
              >
                {busy ? 'Processing…' : faceProfile?.enrolled ? 'Replace Face Profile' : 'Enroll Face Profile'}
              </button>
              {faceProfile?.enrolled && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void revokeFace()}
                  className="rounded-lg border border-rose-200 px-4 py-2 text-xs font-semibold text-rose-800 transition hover:bg-rose-50 disabled:opacity-50"
                >
                  Revoke Enrollment
                </button>
              )}
            </div>
          </form>
        </section>
      )}

      {/* Change Password via Email OTP (No Current Password Required) */}
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <KeyRound size={16} className="text-primary-dark" />
            <h2 className="text-sm font-semibold text-slate-900">Change password via email verification</h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            For security, no current password is required. A 6-digit one-time code will be dispatched to your registered email ({me?.email || currentUser.email}).
          </p>
        </div>

        {!otpSent ? (
          <div className="pt-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void requestOtp()}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
            >
              <Mail size={14} />
              {busy ? 'Sending verification code…' : 'Send Verification Code to Email'}
            </button>
          </div>
        ) : (
          <form onSubmit={verifyAndChangePassword} className="space-y-4 pt-2">
            {devOtpHint && (
              <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-xs text-sky-800">
                <span className="font-bold">Development Mode OTP:</span> <span className="font-mono text-sm font-bold text-sky-900">{devOtpHint}</span> (also sent via email).
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-xs font-medium text-slate-700">
                6-digit verification code
                <input
                  required
                  maxLength={6}
                  pattern="\d{6}"
                  placeholder="123456"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  className={`${field} font-mono tracking-widest text-center text-base`}
                />
              </label>

              <div className="flex items-end">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void requestOtp()}
                  className="mb-1 text-xs font-semibold text-primary hover:underline"
                >
                  Resend code
                </button>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-xs font-medium text-slate-700">
                New password (min 12 characters)
                <input
                  required
                  minLength={12}
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className={field}
                />
              </label>

              <label className="block text-xs font-medium text-slate-700">
                Confirm new password
                <input
                  required
                  minLength={12}
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={field}
                />
              </label>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={busy || otpCode.length !== 6 || newPassword.length < 12}
                className="rounded-lg bg-primary px-5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
              >
                {busy ? 'Updating password…' : 'Verify & Set New Password'}
              </button>
              <button
                type="button"
                onClick={() => setOtpSent(false)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
};
