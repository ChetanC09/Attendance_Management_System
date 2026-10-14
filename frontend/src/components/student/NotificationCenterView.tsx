import React, { useEffect, useMemo, useState } from 'react';
import { Bell, Check } from 'lucide-react';
import { api } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Item = { id: string; title: string; message: string; channel: string; status: string; payload: Record<string, unknown> | null; read_at: string | null; created_at: string; announcement?: boolean };
type Announcement = { id: string; title: string; body: string; created_at: string };
type Filter = 'all' | 'unread' | 'read';

export const NotificationCenterView: React.FC = () => {
  const { currentRole, markNotificationAsRead, markAllNotificationsAsRead } = useApp();
  const [items, setItems] = useState<Item[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    const notificationRequest = api<Item[]>('/api/notifications');
    const announcementRequest = currentRole === 'student'
      ? api<Announcement[]>('/api/student/announcements').catch(() => [] as Announcement[])
      : Promise.resolve([] as Announcement[]);
    void Promise.all([notificationRequest, announcementRequest])
      .then(([notifications, announcements]) => {
        if (!active) return;
        const announcementItems: Item[] = announcements.map((item) => ({
          id: `announcement-${item.id}`,
          title: item.title,
          message: item.body,
          channel: 'ANNOUNCEMENT',
          status: 'PUBLISHED',
          payload: null,
          read_at: item.created_at,
          created_at: item.created_at,
          announcement: true,
        }));
        setItems([...notifications, ...announcementItems].sort((a, b) => b.created_at.localeCompare(a.created_at)));
      })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Notifications could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [currentRole]);

  const visible = useMemo(() => items.filter((item) => filter === 'all' || (filter === 'unread' ? !item.read_at : Boolean(item.read_at))), [items, filter]);
  const markRead = async (item: Item) => {
    setBusy(item.id); setError('');
    try {
      await markNotificationAsRead(item.id);
      setItems((previous) => previous.map((row) => row.id === item.id ? { ...row, read_at: new Date().toISOString() } : row));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not mark notification as read.');
    } finally { setBusy(null); }
  };

  const markAllRead = async () => {
    setBusy('all'); setError('');
    try {
      await markAllNotificationsAsRead();
      const now = new Date().toISOString();
      setItems((previous) => previous.map((item) => !item.announcement && !item.read_at ? { ...item, read_at: now } : item));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not mark notifications as read.');
    } finally { setBusy(null); }
  };

  const heading = currentRole === 'student' ? 'Notifications & announcements' : 'Notifications';
  return <div className="mx-auto w-full max-w-6xl space-y-5">
    <header><p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">{currentRole} · live API</p><h1 className="text-2xl font-semibold tracking-tight text-slate-900">{heading}</h1><p className="mt-1 text-sm text-slate-600">{currentRole === 'student' ? 'Account notifications and announcements published to your assigned course sections.' : 'Account notifications delivered to your signed-in account.'}</p></header>
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 p-2"><nav className="flex gap-1" aria-label="Filter notifications">{(['all', 'unread', 'read'] as Filter[]).map((value) => <button type="button" key={value} aria-pressed={filter === value} onClick={() => setFilter(value)} className={`rounded-lg px-3 py-2 text-xs capitalize ${filter === value ? 'bg-primary-container text-primary-dark' : 'text-slate-600'}`}>{value}</button>)}</nav>{items.some((item) => !item.read_at && !item.announcement) && <button type="button" disabled={busy !== null} onClick={() => void markAllRead()} className="rounded-lg px-3 py-2 text-xs font-semibold text-primary-dark disabled:opacity-50">{busy === 'all' ? 'Saving…' : 'Mark all read'}</button>}</div>
      {loading ? <p className="p-6 text-sm text-slate-500">Loading notifications…</p> : visible.length ? <ul className="divide-y divide-slate-100">{visible.map((item) => <li key={item.id} className={`flex gap-3 p-4 sm:px-5 ${!item.read_at ? 'bg-orange-50/30' : ''}`}><Bell size={17} className="mt-1 shrink-0 text-primary-dark"/><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-sm font-semibold text-slate-900">{item.title}</h2><span className="text-[11px] text-slate-500">{item.channel} · {item.status}</span><time className="text-[11px] text-slate-500">{new Date(item.created_at).toLocaleString()}</time></div><p className="mt-1 whitespace-pre-wrap text-sm leading-5 text-slate-600">{item.message}</p>{!item.read_at && !item.announcement && <button type="button" disabled={busy !== null} onClick={() => void markRead(item)} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary-dark disabled:opacity-50"><Check size={13}/>{busy === item.id ? 'Saving…' : 'Mark read'}</button>}</div></li>)}</ul> : <p className="p-8 text-center text-sm text-slate-500">No notifications to show.</p>}
    </section>
  </div>;
};
