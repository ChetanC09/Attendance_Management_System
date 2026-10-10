import React, { useEffect, useState } from 'react';
import { ArrowRight, CalendarDays, FileClock, Video } from 'lucide-react';
import { api } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Lecture = { id: string; allocation_id: string; starts_at: string; ends_at: string; status: string };
type Timetable = { allocation_id?: string; weekday: number; starts_at: string; ends_at: string; course_code: string; course_name: string; classroom_code: string; classroom_name: string };
type Request = { id: string; status: string };

export const FacultyOverviewView: React.FC = () => {
  const { currentUser, setCurrentRoute } = useApp();
  const [lectures, setLectures] = useState<Lecture[]>([]); const [schedule, setSchedule] = useState<Timetable[]>([]);
  const [requests, setRequests] = useState<Request[]>([]); const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  useEffect(() => { Promise.all([api<Lecture[]>('/api/faculty/lectures/today'), api<Timetable[]>('/api/faculty/timetable/overview'), api<Request[]>('/api/faculty/requests')]).then(([today, timetable, requestRows]) => { setLectures(today); setSchedule(timetable); setRequests(requestRows); }).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  const pending = requests.filter((r) => r.status === 'PENDING').length;
  const details = (allocation: string) => schedule.find((item) => item.allocation_id === allocation);
  const clock = (value: string) => new Date(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return <div className="mx-auto w-full max-w-6xl space-y-6"><header><p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Faculty · live API</p><h1 className="text-2xl font-semibold text-slate-900">Welcome, {currentUser.name}</h1><p className="mt-1 text-sm text-slate-600">Today’s teaching schedule and requests that need your attention.</p></header>
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {loading ? <p className="text-sm text-slate-500">Loading your faculty overview…</p> : <>
      <section className="grid gap-4 sm:grid-cols-3"><article className="rounded-2xl border bg-white p-5"><p className="text-xs text-slate-500">Today’s lectures</p><p className="mt-2 font-mono text-3xl font-semibold">{lectures.length}</p></article><button onClick={() => setCurrentRoute('faculty-approvals')} className="rounded-2xl border bg-white p-5 text-left"><p className="text-xs text-slate-500">Pending requests</p><p className="mt-2 font-mono text-3xl font-semibold">{pending}</p><span className="text-xs font-semibold text-primary-dark">Review requests →</span></button><button onClick={() => setCurrentRoute('camera-attendance-session')} className="rounded-2xl border border-primary/30 bg-primary-container/30 p-5 text-left"><p className="text-xs text-slate-600">Ready to take attendance?</p><span className="mt-2 flex items-center gap-2 text-lg font-semibold text-primary-dark"><Video size={18}/>Start attendance</span><span className="mt-1 block text-xs text-slate-600">Open a session for a scheduled class</span></button></section>
      <section className="rounded-2xl border bg-white"><div className="flex items-center justify-between border-b p-5"><div className="flex items-center gap-2"><CalendarDays size={17} className="text-primary-dark"/><div><h2 className="text-sm font-semibold">Today’s assigned classes</h2><p className="mt-1 text-xs text-slate-500">Course and classroom details from your timetable.</p></div></div><button onClick={() => setCurrentRoute('faculty-timetable')} className="inline-flex items-center gap-1 text-xs font-semibold text-primary-dark">Full timetable <ArrowRight size={14}/></button></div>{lectures.length ? <ul className="divide-y">{lectures.map((item) => { const info = details(item.allocation_id); return <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 p-4"><span><span className="block text-sm font-semibold">{clock(item.starts_at)} – {clock(item.ends_at)}{info ? ` · ${info.course_code} ${info.course_name}` : ''}</span><span className="text-xs text-slate-500">{info ? `${info.classroom_code} · ${info.classroom_name}` : 'Course details unavailable'} · {item.status}</span></span><button onClick={() => setCurrentRoute('camera-attendance-session')} className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white">Take attendance</button></li>; })}</ul> : <p className="p-6 text-sm text-slate-500">No lectures scheduled today.</p>}</section>
      <button onClick={() => setCurrentRoute('faculty-analytics')} className="flex items-center gap-3 rounded-xl border bg-white p-4 text-left"><FileClock size={18} className="text-primary-dark"/><span className="text-sm font-semibold">Review attendance analytics and defaulters</span><ArrowRight size={15} className="ml-auto"/></button>
    </>}
  </div>;
};
