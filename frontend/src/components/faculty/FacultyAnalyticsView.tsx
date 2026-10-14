import React, { useEffect, useState } from 'react';
import {
  Bell,
  Download,
  FileSpreadsheet,
  FileText,
  Search,
  ShieldAlert,
  Users,
} from 'lucide-react';
import { api, apiBaseUrl } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Allocation = {
  allocation_id: string;
  course_code: string;
  course_name: string;
  section_name: string;
};

type Defaulter = {
  student_id: string;
  institutional_id: string;
  full_name: string;
  attended_lectures: number;
  conducted_lectures: number;
  attendance_percentage: number;
};

type Trend = {
  lecture_id: string;
  starts_at: string;
  recorded: number;
  attended: number;
  attendance_percentage: number;
};

export const FacultyAnalyticsView: React.FC = () => {
  const { addToast } = useApp();
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [allocation, setAllocation] = useState('');
  const [threshold, setThreshold] = useState(75);
  const [rows, setRows] = useState<Defaulter[]>([]);
  const [trend, setTrend] = useState<Trend[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api<Allocation[]>('/api/faculty/analytics/allocations')
      .then((list) => {
        setAllocations(list);
        setAllocation(list[0]?.allocation_id || '');
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load course allocations.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!allocation) {
      setRows([]);
      setTrend([]);
      return;
    }
    let active = true;
    setAnalyticsLoading(true);
    setError('');
    Promise.all([
      api<Defaulter[]>(`/api/faculty/analytics/defaulters?allocation_id=${encodeURIComponent(allocation)}&threshold=${threshold}`),
      api<Trend[]>(`/api/faculty/analytics/trend?allocation_id=${encodeURIComponent(allocation)}`),
    ])
      .then(([defaulters, history]) => {
        if (active) {
          setRows(defaulters);
          setTrend(history);
        }
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : 'Failed to fetch analytics.');
      })
      .finally(() => {
        if (active) setAnalyticsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allocation, threshold]);

  const selected = allocations.find((item) => item.allocation_id === allocation);

  const downloadDefaultersPdf = () => {
    if (!allocation) return;
    const url = `${apiBaseUrl}/api/faculty/analytics/defaulters/pdf?allocation_id=${encodeURIComponent(allocation)}&threshold=${threshold}`;
    window.open(url, '_blank');
  };

  const downloadStudentPdf = (studentId: string) => {
    const url = `${apiBaseUrl}/api/faculty/analytics/student/${encodeURIComponent(studentId)}/pdf`;
    window.open(url, '_blank');
  };

  const notifyDefaulters = async () => {
    if (!allocation || !rows.length) return;
    setNotifying(true);
    try {
      const res = await api<{ notified_count: number }>(
        `/api/faculty/analytics/defaulters/notify?allocation_id=${encodeURIComponent(allocation)}&threshold=${threshold}`,
        { method: 'POST' }
      );
      addToast({
        type: 'success',
        message: `Notification sent to ${res.notified_count} defaulter student(s).`,
      });
    } catch (e) {
      addToast({
        type: 'error',
        message: e instanceof Error ? e.message : 'Could not notify students.',
      });
    } finally {
      setNotifying(false);
    }
  };

  const filteredRows = rows.filter(
    (row) =>
      row.full_name.toLowerCase().includes(search.toLowerCase()) ||
      row.institutional_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Faculty · Course Standing</p>
          <h1 className="text-2xl font-semibold text-slate-900">Attendance Analytics & Defaulters</h1>
          <p className="mt-1 text-sm text-slate-600">
            Monitor class trends, generate formal PDF reports, and alert students at risk of attendance shortfalls.
          </p>
        </div>

        {allocation && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={downloadDefaultersPdf}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              <Download size={14} className="text-slate-500" />
              Export Defaulters PDF
            </button>
            <button
              type="button"
              disabled={notifying || !rows.length}
              onClick={() => void notifyDefaulters()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
            >
              <Bell size={14} />
              {notifying ? 'Sending alerts…' : `Notify Defaulters (${rows.length})`}
            </button>
          </div>
        )}
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

      {/* Allocation & Threshold Filters */}
      <section className="flex flex-wrap items-end gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <label className="min-w-64 flex-1 text-sm font-medium text-slate-700">
          Assigned course and section
          <select
            disabled={loading || !allocations.length}
            value={allocation}
            onChange={(e) => setAllocation(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-slate-200 p-2.5 text-sm outline-none focus:border-primary"
          >
            <option value="">{allocations.length ? 'Choose course allocation…' : 'No allocations assigned'}</option>
            {allocations.map((item) => (
              <option key={item.allocation_id} value={item.allocation_id}>
                {item.course_code} · {item.course_name} — Section {item.section_name}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm font-medium text-slate-700">
          Threshold (%)
          <div className="mt-1.5 flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="100"
              value={threshold}
              onChange={(e) => setThreshold(Math.max(0, Math.min(100, Number(e.target.value))))}
              className="block w-28 rounded-lg border border-slate-200 p-2 text-sm outline-none focus:border-primary"
            />
            <span className="text-xs text-slate-500">Min. required</span>
          </div>
        </label>
      </section>

      {selected && (
        <div className="flex items-center justify-between rounded-xl bg-slate-100/70 px-4 py-2 text-xs font-medium text-slate-700">
          <span>
            <b>Course:</b> {selected.course_code} — {selected.course_name}
          </span>
          <span>
            <b>Section:</b> {selected.section_name}
          </span>
        </div>
      )}

      {/* Trend Progress Bar */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5">
          <h2 className="text-sm font-semibold text-slate-900">Attendance trend across past lectures</h2>
          <p className="mt-1 text-xs text-slate-500">
            Percentage of roster marked present or late for each conducted class.
          </p>
        </div>
        {analyticsLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading lecture trend…</p>
        ) : trend.length ? (
          <div className="space-y-3 p-5">
            {trend.map((item) => (
              <div key={item.lecture_id} className="grid grid-cols-[120px_1fr_90px] items-center gap-4 text-xs">
                <time className="font-mono text-slate-600">{new Date(item.starts_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</time>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all ${
                      item.attendance_percentage >= threshold
                        ? 'bg-emerald-500'
                        : item.attendance_percentage >= 50
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.max(0, Math.min(100, item.attendance_percentage))}%` }}
                  />
                </div>
                <span className="text-right font-mono font-semibold text-slate-700">
                  {item.attendance_percentage}% <span className="font-normal text-slate-400">({item.attended}/{item.recorded})</span>
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="p-6 text-sm text-slate-500">No lecture attendance entries recorded yet for this course.</p>
        )}
      </section>

      {/* Defaulters Table */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <ShieldAlert size={16} className={rows.length ? 'text-rose-600' : 'text-slate-400'} />
              Students Below {threshold}% Required Threshold
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {rows.length} student{rows.length === 1 ? '' : 's'} flagged as defaulters
            </p>
          </div>

          {rows.length > 0 && (
            <div className="relative min-w-[200px]">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search defaulters…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-lg border border-slate-200 pl-8 pr-3 py-1.5 text-xs outline-none focus:border-primary"
              />
            </div>
          )}
        </div>

        {analyticsLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading defaulters…</p>
        ) : filteredRows.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50 text-xs text-slate-500">
                  <th className="px-5 py-3">Student Name</th>
                  <th className="px-4 py-3">Attended / Total</th>
                  <th className="px-4 py-3">Attendance Rate</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Individual PDF Report</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRows.map((row) => (
                  <tr key={row.student_id} className="transition hover:bg-slate-50/70">
                    <td className="px-5 py-3.5">
                      <span className="block font-medium text-slate-900">{row.full_name}</span>
                      <span className="font-mono text-xs text-slate-500">{row.institutional_id}</span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs">
                      {row.attended_lectures} / {row.conducted_lectures} lectures
                    </td>
                    <td className="px-4 py-3.5 font-mono text-sm font-semibold text-rose-700">
                      {row.attendance_percentage.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800">
                        DEFAULTER
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => downloadStudentPdf(row.student_id)}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                        title="Download official PDF attendance transcript"
                      >
                        <FileText size={13} />
                        Statement (PDF)
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-sm text-slate-500">
            {rows.length ? 'No defaulters match your search filter.' : `✓ Excellent! No students are below ${threshold}% in this course allocation.`}
          </div>
        )}
      </section>
    </div>
  );
};
