import React, { useEffect, useState } from 'react';
import { ArrowRight, Building2, ClipboardList, GraduationCap, Settings2, Users } from 'lucide-react';
import { api } from '../../services/api';
import { useApp } from '../../context/AppContext';

type User = { role: string };
type RecordItem = { id: string; code?: string; name?: string };
type Overview = {
  departments: number; courses: number; lectures: number; attendance_records: number;
  recorded_attendance_percentage: number; pending_requests: number; open_attendance_sessions: number;
  active_users: number; low_attendance_course_records: number;
};

export const AdminDashboardView: React.FC = () => {
  const { setCurrentRoute, currentUser } = useApp();
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<RecordItem[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      api<User[]>('/api/admin/users?limit=500'),
      api<RecordItem[]>('/api/admin/departments'),
      api<Overview>('/api/admin/overview'),
    ]).then(([accountRows, departmentRows, stats]) => {
      setUsers(accountRows); setDepartments(departmentRows); setOverview(stats);
    }).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  const metric = (label: string, value: string | number, route?: string, note?: string) => {
    const content = <><span className="text-xs text-slate-500">{label}</span><span className="mt-2 block font-mono text-3xl font-semibold">{loading ? '—' : value}</span>{note && <span className="mt-1 block text-xs text-slate-500">{note}</span>}</>;
    return route ? <button key={label} onClick={() => setCurrentRoute(route)} className="rounded-2xl border bg-white p-5 text-left hover:border-primary-light">{content}</button> : <article key={label} className="rounded-2xl border bg-white p-5">{content}</article>;
  };
  return <div className="mx-auto w-full max-w-6xl space-y-6">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Administrator · live API</p><h1 className="text-2xl font-semibold text-slate-900">Academic operations</h1><p className="mt-1 text-sm text-slate-600">System activity and configuration for {currentUser.name}.</p></div><button onClick={() => setCurrentRoute('governance')} className="inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold"><Settings2 size={16}/>Settings</button></header>
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {metric('User accounts', overview?.active_users ?? users.length, 'admin-users', 'Active accounts')}
      {metric('Departments', overview?.departments ?? 0, 'admin-departments')}
      {metric('Courses', overview?.courses ?? 0, 'admin-courses')}
      {metric('Scheduled lectures', overview?.lectures ?? 0, 'admin-timetable')}
    </section>
    <section className="grid gap-4 sm:grid-cols-3">
      {metric('Attendance rate', `${overview?.recorded_attendance_percentage ?? 0}%`, undefined, `${overview?.attendance_records ?? 0} marks · attended or excused`)}
      {metric('Pending exceptions', overview?.pending_requests ?? 0, undefined, 'Requests awaiting faculty review')}
      {metric('Low attendance course records', overview?.low_attendance_course_records ?? 0, undefined, 'Student-course records below the configured threshold')}
      {metric('Open sessions', overview?.open_attendance_sessions ?? 0, undefined, 'Attendance sessions in progress')}
    </section>
    <section className="rounded-2xl border bg-white"><div className="flex items-center justify-between border-b p-5"><div><h2 className="text-sm font-semibold">Departments</h2><p className="mt-1 text-xs text-slate-500">Directory records from academic administration.</p></div><button onClick={() => setCurrentRoute('admin-academic-structure')} className="inline-flex items-center gap-1 text-xs font-semibold text-primary-dark">Academic structure <ArrowRight size={14}/></button></div>{departments.length ? <ul className="divide-y">{departments.slice(0, 8).map((item) => <li key={item.id} className="flex items-center justify-between px-5 py-3 text-sm"><span>{item.name}</span><span className="font-mono text-xs text-slate-500">{item.code}</span></li>)}</ul> : <p className="p-6 text-sm text-slate-500">No departments found.</p>}</section>
    <section className="grid gap-3 sm:grid-cols-3"><button onClick={() => setCurrentRoute('admin-users')} className="flex items-center gap-3 rounded-xl border bg-white p-4 text-left"><Users size={18} className="text-primary-dark"/><span className="text-sm font-semibold">Manage accounts</span></button><button onClick={() => setCurrentRoute('system-logs-settings')} className="flex items-center gap-3 rounded-xl border bg-white p-4 text-left"><ClipboardList size={18} className="text-primary-dark"/><span className="text-sm font-semibold">Audit activity</span></button><button onClick={() => setCurrentRoute('governance')} className="flex items-center gap-3 rounded-xl border bg-white p-4 text-left"><Building2 size={18} className="text-primary-dark"/><span className="text-sm font-semibold">Attendance settings</span></button><button onClick={() => setCurrentRoute('admin-courses')} className="flex items-center gap-3 rounded-xl border bg-white p-4 text-left"><GraduationCap size={18} className="text-primary-dark"/><span className="text-sm font-semibold">Course catalogue</span></button></section>
  </div>;
};
