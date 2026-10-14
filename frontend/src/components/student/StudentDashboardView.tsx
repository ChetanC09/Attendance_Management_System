import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileClock,
  Sparkles,
  TriangleAlert,
} from 'lucide-react';
import { api, apiBaseUrl } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Summary = {
  course_id: string;
  course_code: string;
  course_name: string;
  conducted_lectures: number;
  attended_lectures: number;
  attendance_percentage: number;
};

type Request = { id: string; status: string };
type Overall = {
  attended_lectures: number;
  conducted_lectures: number;
  attendance_percentage: number;
};

export const StudentDashboardView: React.FC = () => {
  const { currentUser, setCurrentRoute } = useApp();
  const [courses, setCourses] = useState<Summary[]>([]);
  const [requests, setRequests] = useState<Request[]>([]);
  const [overall, setOverall] = useState<Overall | null>(null);
  const [threshold, setThreshold] = useState(75);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api<Summary[]>('/api/student/attendance'),
      api<Request[]>('/api/student/requests'),
      api<Overall>('/api/student/analytics/overall'),
      api<{ attendance_threshold: number }>('/api/student/attendance/threshold').catch(() => ({
        attendance_threshold: 75,
      })),
    ])
      .then(([c, r, o, t]) => {
        setCourses(c);
        setRequests(r);
        setOverall(o);
        setThreshold(t.attendance_threshold);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load dashboard data.'))
      .finally(() => setLoading(false));
  }, []);

  const atRiskCourses = courses.filter((c) => c.attendance_percentage < threshold && c.conducted_lectures > 0);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">
            Student Overview · Live Portal
          </p>
          <h1 className="text-2xl font-semibold text-slate-900">Good to see you, {currentUser.name}</h1>
          <p className="mt-1 text-sm text-slate-600">
            Current attendance standing, risk projections, and leave requests.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => window.open(`${apiBaseUrl}/api/student/analytics/report/pdf`, '_blank')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            <Download size={14} className="text-slate-500" />
            Official Statement (PDF)
          </button>
          <button
            type="button"
            onClick={() => setCurrentRoute('student-face-checkin')}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark"
          >
            <Sparkles size={14} />
            Face Check-in
          </button>
        </div>
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

      {/* Low-Attendance Risk Alert Banner (G1) */}
      {atRiskCourses.length > 0 && (
        <section className="relative overflow-hidden rounded-2xl border border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50 p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-amber-500/20 p-2 text-amber-800">
                <AlertTriangle size={20} />
              </div>
              <div>
                <h2 className="text-base font-bold text-amber-950">
                  Attendance Risk Notice: {atRiskCourses.length} course{atRiskCourses.length === 1 ? '' : 's'} below {threshold}%
                </h2>
                <p className="mt-1 text-xs text-amber-800">
                  Institutional policy requires at least {threshold}% attendance for exam eligibility. The following courses require immediate attention:
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {atRiskCourses.map((c) => (
                    <span
                      key={c.course_id}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white/80 px-2.5 py-1 font-mono text-xs font-bold text-amber-900 shadow-2xs"
                    >
                      <span>{c.course_code}:</span>
                      <span className="text-rose-700">{c.attendance_percentage.toFixed(1)}%</span>
                      <span className="text-[10px] text-amber-700 font-normal">({c.attended_lectures}/{c.conducted_lectures})</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              <button
                type="button"
                onClick={() => setCurrentRoute('recovery-planner')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-700 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-amber-800"
              >
                <ClipboardCheck size={14} />
                Recovery Planner
              </button>
              <button
                type="button"
                onClick={() => setCurrentRoute('regularization-form')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3.5 py-2 text-xs font-semibold text-amber-900 shadow-sm transition hover:bg-amber-50"
              >
                <FileClock size={14} />
                Submit Request
              </button>
            </div>
          </div>
        </section>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading your attendance standing…</p>
      ) : (
        <>
          {/* Key Metrics */}
          <section className="grid gap-4 sm:grid-cols-3">
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-medium text-slate-500">Overall attendance</span>
              <p className="mt-2 font-mono text-3xl font-bold text-slate-900">
                {(overall?.attendance_percentage || 0).toFixed(1)}%
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {overall?.attended_lectures || 0} attended of {overall?.conducted_lectures || 0} conducted
              </p>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-medium text-slate-500">Enrolled courses</span>
              <p className="mt-2 font-mono text-3xl font-bold text-slate-900">{courses.length}</p>
              <p className="mt-1 text-xs text-slate-500">
                {courses.length - atRiskCourses.length} in good standing · {atRiskCourses.length} at risk
              </p>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-medium text-slate-500">Pending requests</span>
              <p className="mt-2 font-mono text-3xl font-bold text-slate-900">
                {requests.filter((r) => r.status === 'PENDING').length}
              </p>
              <button
                type="button"
                onClick={() => setCurrentRoute('leave-medical-slips')}
                className="mt-1 text-xs font-semibold text-primary hover:underline"
              >
                View submitted requests →
              </button>
            </article>
          </section>

          {/* Course Standing List */}
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 p-5">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Course attendance standing</h2>
                <p className="mt-1 text-xs text-slate-500">Institutional threshold: {threshold}%</p>
              </div>
              <button
                type="button"
                onClick={() => setCurrentRoute('course-attendance')}
                className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
              >
                Full details <ArrowRight size={13} />
              </button>
            </div>

            {courses.length ? (
              <ul className="divide-y divide-slate-100">
                {courses.map((course) => {
                  const isBelow = course.attendance_percentage < threshold && course.conducted_lectures > 0;
                  return (
                    <li key={course.course_id} className="flex flex-wrap items-center justify-between gap-4 p-4 transition hover:bg-slate-50/60">
                      <div className="min-w-0 flex-1">
                        <p className="font-mono text-xs font-bold text-primary-dark">{course.course_code}</p>
                        <p className="mt-0.5 truncate text-sm font-semibold text-slate-800">{course.course_name}</p>
                      </div>

                      <div className="flex items-center gap-4">
                        <span className="font-mono text-xs text-slate-500">
                          {course.attended_lectures} / {course.conducted_lectures} classes
                        </span>

                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-xs font-bold ${
                            isBelow ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {course.attendance_percentage.toFixed(1)}%
                          {isBelow ? <TriangleAlert size={12} /> : <CheckCircle2 size={12} />}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="p-8 text-center text-sm text-slate-500">No course attendance recorded yet.</p>
            )}
          </section>

          {/* Quick Shortcuts */}
          <section className="flex flex-wrap gap-4 text-xs font-semibold text-primary-dark">
            <button
              type="button"
              onClick={() => setCurrentRoute('recovery-planner')}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2 shadow-2xs hover:bg-slate-50"
            >
              Open Recovery Planner →
            </button>
            <button
              type="button"
              onClick={() => setCurrentRoute('timetable-schedule')}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2 shadow-2xs hover:bg-slate-50"
            >
              Class Timetable →
            </button>
            <button
              type="button"
              onClick={() => setCurrentRoute('notification-center')}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2 shadow-2xs hover:bg-slate-50"
            >
              Notification Center →
            </button>
          </section>
        </>
      )}
    </div>
  );
};
