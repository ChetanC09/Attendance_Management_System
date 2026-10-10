import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Download, Search } from 'lucide-react';
import { api } from '../../services/api';
import { useApp } from '../../context/AppContext';

type RecordItem = { lecture_id: string; starts_at: string; course_id?: string; course_code: string; course_name: string; status: string | null };
const csvCell = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`;

export const AttendanceHistoryView: React.FC = () => {
  const { currentRoute, setCurrentRoute } = useApp();
  const courseId = currentRoute.startsWith('attendance-history/') ? currentRoute.slice('attendance-history/'.length) : '';
  const [rows, setRows] = useState<RecordItem[]>([]);
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true); setError('');
    const filter = courseId ? `&course_id=${encodeURIComponent(courseId)}` : '';
    api<RecordItem[]>(`/api/student/attendance/history?limit=500${filter}`).then(setRows).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [courseId]);
  const filtered = useMemo(() => rows.filter((row) => (status === 'all' || (row.status || 'UNMARKED') === status) && `${row.course_code} ${row.course_name} ${row.status || ''}`.toLowerCase().includes(search.trim().toLowerCase())), [rows, status, search]);
  const exportCsv = () => {
    const csv = [['lecture_id', 'starts_at', 'course_code', 'course_name', 'status'], ...filtered.map((r) => [r.lecture_id, r.starts_at, r.course_code, r.course_name, r.status || 'unmarked'])].map((row) => row.map(csvCell).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' })); const link = document.createElement('a'); link.href = url; link.download = 'attendance-history.csv'; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="mx-auto w-full max-w-6xl space-y-5"><header className="flex flex-wrap items-end justify-between gap-3"><div>{courseId && <button onClick={() => setCurrentRoute('course-attendance')} className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-primary-dark"><ArrowLeft size={15}/> All courses</button>}<p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Student · live API</p><h1 className="text-2xl font-semibold text-slate-900">{courseId && rows[0] ? `${rows[0].course_code} · ${rows[0].course_name}` : 'Attendance history'}</h1><p className="mt-1 text-sm text-slate-600">{courseId ? 'Lecture-by-lecture attendance for this course.' : 'Session history from your enrolled section.'}</p></div><button disabled={!filtered.length} onClick={exportCsv} className="inline-flex items-center gap-2 rounded-lg border px-3.5 py-2.5 text-sm font-semibold disabled:opacity-50"><Download size={16}/>Export CSV</button></header>{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}<section className="overflow-hidden rounded-2xl border bg-white"><div className="grid gap-2 border-b p-4 sm:grid-cols-[1fr_auto]"><label className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input aria-label="Search course attendance" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search attendance" className="w-full rounded-lg border py-2 pl-9 pr-3 text-sm"/></label><label className="flex items-center gap-2 text-xs">Status<select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border p-2"><option value="all">All statuses</option><option value="PRESENT">Present</option><option value="LATE">Late</option><option value="ABSENT">Absent</option><option value="EXCUSED">Excused</option><option value="UNMARKED">Unmarked</option></select></label></div>{loading ? <p className="p-6 text-sm text-slate-500">Loading attendance history…</p> : filtered.length ? <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><thead><tr className="border-b text-xs text-slate-500"><th className="px-5 py-3">Date & time</th>{!courseId && <th className="px-4 py-3">Course</th>}<th className="px-4 py-3">Lecture</th><th className="px-5 py-3">Status</th></tr></thead><tbody className="divide-y">{filtered.map((row) => <tr key={row.lecture_id}><td className="px-5 py-3">{new Date(row.starts_at).toLocaleString()}</td>{!courseId && <td className="px-4 py-3">{row.course_code} · {row.course_name}</td>}<td className="px-4 py-3 font-mono text-xs">{row.lecture_id.slice(0, 8)}</td><td className="px-5 py-3">{row.status || 'Unmarked'}</td></tr>)}</tbody></table></div> : <p className="p-8 text-center text-sm text-slate-500">No matching attendance records.</p>}</section></div>;
};
