import React, { useEffect, useState } from 'react';
import { api, jsonBody, type ApiUser } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Preference = { channel: string; enabled: boolean };
const field = 'mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-primary';

export const AccountSettingsView: React.FC = () => {
  const { currentUser, currentRole, signOut } = useApp();
  const [me, setMe] = useState<ApiUser | null>(null);
  const [prefs, setPrefs] = useState<Preference[]>([]);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<ApiUser>('/api/auth/me').then(setMe);
    api<Preference[]>('/api/notifications/preferences').then(setPrefs).catch(() => setPrefs([]));
  }, []);

  const changePassword = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setMessage('');
    if (newPassword.length < 12 || newPassword !== confirmPassword) { setError('New password must be at least 12 characters and both entries must match.'); return; }
    setBusy(true);
    try {
      await api<void>('/api/auth/change-password', { method: 'POST', body: jsonBody({ current_password: currentPassword, new_password: newPassword }) });
      setMessage('Password updated. Please sign in again.'); await signOut();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Password could not be changed.'); }
    finally { setBusy(false); }
  };

  const setPreference = async (channel: string, enabled: boolean) => {
    setError('');
    try {
      await api(`/api/notifications/preferences/${channel}?enabled=${enabled}`, { method: 'PUT' });
      setPrefs((old) => [...old.filter((item) => item.channel !== channel), { channel, enabled }]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Preference could not be saved.'); }
  };

  const enrollFace = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setMessage('');
    if (!consent || !faceFile) { setError('Explicit consent and one image are required.'); return; }
    setBusy(true);
    const form = new FormData(); form.append('consent', 'true'); form.append('image', faceFile);
    try { await api('/api/student/face-profile/enroll', { method: 'POST', body: form }); setMessage('Face profile enrolled. The server stores the derived face embedding.'); setFaceFile(null); setConsent(false); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Enrollment failed. Check image quality and vision service availability.'); }
    finally { setBusy(false); }
  };

  const revokeFace = async () => {
    setError(''); setMessage(''); setBusy(true);
    try { await api<void>('/api/student/face-profile', { method: 'DELETE' }); setMessage('Face profile consent revoked and profile disabled.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not revoke face enrollment.'); }
    finally { setBusy(false); }
  };

  return <div className="mx-auto w-full max-w-4xl space-y-5">
    <header><p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Account · live API</p><h1 className="text-2xl font-semibold text-slate-900">Profile & settings</h1><p className="mt-1 text-sm text-slate-600">Manage account security and notification preferences.</p></header>
    {error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}{message && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
    <section className="rounded-2xl border bg-white p-5"><h2 className="text-sm font-semibold">Account</h2><dl className="mt-4 grid gap-4 sm:grid-cols-2">{[['Name', me?.full_name || currentUser.name], ['Email', me?.email || currentUser.email], ['Institutional ID', me?.institutional_id || currentUser.rollOrEmpId], ['Role', me?.role || currentRole.toUpperCase()]].map(([label, value]) => <div key={label}><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 text-sm font-medium">{value}</dd></div>)}</dl></section>
    <section className="rounded-2xl border bg-white p-5"><h2 className="text-sm font-semibold">Notification preferences</h2><p className="mt-1 text-xs text-slate-500">Optional delivery-channel preferences for your account.</p><div className="mt-3 flex flex-wrap gap-3">{['IN_APP', 'EMAIL', 'SMS'].map((channel) => { const item = prefs.find((preference) => preference.channel === channel); return <label key={channel} className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"><input type="checkbox" checked={item?.enabled || false} onChange={(event) => void setPreference(channel, event.target.checked)} />{channel.replace('_', ' ')}</label>; })}</div></section>
    {currentRole === 'student' && <section className="space-y-4 rounded-2xl border bg-white p-5"><div><h2 className="text-sm font-semibold">Face attendance enrollment</h2><p className="mt-1 text-xs leading-5 text-slate-500">Enrollment is optional and requires explicit consent. The API processes one face image to derive an embedding; it does not store the uploaded image.</p></div><form onSubmit={enrollFace} className="space-y-3"><label className="block text-sm">Enrollment image (JPEG or PNG)<input required type="file" accept="image/jpeg,image/png" onChange={(event) => setFaceFile(event.target.files?.[0] || null)} className="mt-1 block w-full text-sm" /></label><label className="flex items-start gap-2 text-xs leading-5 text-slate-700"><input required type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-1" />I consent to processing my face image to create an attendance recognition profile.</label><div className="flex flex-wrap gap-2"><button disabled={busy || !faceFile || !consent} className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Processing…' : 'Enroll face profile'}</button><button type="button" disabled={busy} onClick={() => void revokeFace()} className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-800 disabled:opacity-50">Revoke enrollment</button></div></form></section>}
    <form onSubmit={changePassword} className="space-y-3 rounded-2xl border bg-white p-5"><h2 className="text-sm font-semibold">Change password</h2><label className="block max-w-md text-xs font-medium text-slate-600">Current password<input required type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} className={field} /></label><label className="block max-w-md text-xs font-medium text-slate-600">New password<input required minLength={12} type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className={field} /></label><label className="block max-w-md text-xs font-medium text-slate-600">Confirm new password<input required minLength={12} type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className={field} /></label><p className="text-xs text-slate-500">The server revokes the current session after a successful password change.</p><button disabled={busy} className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Saving…' : 'Update password'}</button></form>
  </div>;
};
