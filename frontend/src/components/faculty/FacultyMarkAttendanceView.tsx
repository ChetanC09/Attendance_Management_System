import React, { useCallback, useEffect, useState } from 'react';
import {
  Check,
  CheckCircle2,
  Clock,
  Play,
  RotateCcw,
  Search,
  Square,
  Users,
  Wifi,
  WifiOff,
  XCircle,
} from 'lucide-react';
import { api, apiBaseUrl, jsonBody } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Lecture = {
  id: string;
  allocation_id: string;
  starts_at: string;
  ends_at: string;
  status: string;
};

type Session = {
  id: string;
  lecture_id: string;
  status: string;
};

type Roster = {
  student_id: string;
  institutional_id: string;
  full_name: string;
  attendance_id: string | null;
  status: string | null;
  source: string | null;
  reason: string | null;
};

type SocketState = 'disconnected' | 'connecting' | 'live' | 'polling' | 'offline';

type TimetableItem = {
  allocation_id: string;
  weekday: number;
  starts_at: string;
  ends_at: string;
  course_code: string;
  course_name: string;
  classroom_code: string;
  classroom_name: string;
};

export const FacultyMarkAttendanceView: React.FC<{ mode?: string }> = () => {
  const { addToast, currentUser, selectedLectureId, setSelectedLectureId } = useApp();
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [schedule, setSchedule] = useState<TimetableItem[]>([]);
  const [lectureId, setLectureId] = useState('');
  const [session, setSession] = useState<Session | null>(null);
  const [roster, setRoster] = useState<Roster[]>([]);
  const [edit, setEdit] = useState<Record<string, { status: string; reason: string }>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [search, setSearch] = useState('');
  const [socketStatus, setSocketStatus] = useState<SocketState>('disconnected');

  type NetworkBinding = {
    detected_ip: string;
    bound_subnet: string;
    enforced: boolean;
    bound_at?: string;
  };
  const [networkStatus, setNetworkStatus] = useState<NetworkBinding | null>(null);

  const loadNetwork = useCallback(async (sessionId: string) => {
    try {
      const data = await api<NetworkBinding>(`/api/faculty/attendance/session/${sessionId}/network`);
      setNetworkStatus(data);
    } catch {
      // Ignore network lookup errors
    }
  }, []);

  const handleToggleEnforcement = async () => {
    if (!session) return;
    try {
      const next = !networkStatus?.enforced;
      const updated = await api<NetworkBinding>(`/api/faculty/attendance/session/${session.id}/network`, {
        method: 'POST',
        body: jsonBody({ enforced: next }),
      });
      setNetworkStatus(updated);
      addToast(next ? 'Classroom Wi-Fi lock enabled' : 'Demo Mode enabled: students on any network can check in', 'info');
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Failed to update network lock', 'error');
    }
  };

  const handleRedetectNetwork = async () => {
    if (!session) return;
    try {
      const updated = await api<NetworkBinding>(`/api/faculty/attendance/session/${session.id}/network`, {
        method: 'POST',
        body: jsonBody({ auto_detect: true, enforced: true }),
      });
      setNetworkStatus(updated);
      addToast(`Detected & bound: ${updated.bound_subnet} (IP: ${updated.detected_ip})`, 'success');
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Failed to detect network', 'error');
    }
  };

  const sessionKey = `ams-open-attendance-session:${currentUser.id}`;

  const loadRoster = useCallback(async (sessionId: string) => {
    const data = await api<Roster[]>(`/api/faculty/attendance/session/${sessionId}/roster`);
    setRoster(data);
  }, []);

  useEffect(() => {
    let active = true;
    const restore = async () => {
      setLoading(true);
      setError('');
      try {
        const [today, timetable] = await Promise.all([
          api<Lecture[]>('/api/faculty/lectures/today'),
          api<TimetableItem[]>('/api/faculty/timetable/overview').catch(() => [] as TimetableItem[]),
        ]);
        if (!active) return;
        const scheduled = today.filter((item) => item.status === 'SCHEDULED');
        setLectures(scheduled);
        setSchedule(timetable);
        const preferredLecture = scheduled.find((item) => item.id === selectedLectureId)?.id;
        setLectureId(preferredLecture || scheduled[0]?.id || '');

        const savedId = window.sessionStorage.getItem(sessionKey);
        let restored: Session | null = null;
        if (savedId) {
          try {
            restored = await api<Session>(`/api/faculty/attendance/session/${encodeURIComponent(savedId)}`);
          } catch {
            window.sessionStorage.removeItem(sessionKey);
          }
        }
        if (!restored || restored.status !== 'OPEN') {
          if (restored) window.sessionStorage.removeItem(sessionKey);
          // Session storage is tab-local. Discover sessions from the API so a
          // faculty member can recover after changing roles or opening a new tab.
          const openSessions = await api<Session[]>('/api/faculty/attendance/sessions/open');
          restored = openSessions[0] ?? null;
        }
        if (!active) return;
        if (restored?.status === 'OPEN') {
          window.sessionStorage.setItem(sessionKey, restored.id);
          setSession(restored);
          void loadNetwork(restored.id);
          try {
            await loadRoster(restored.id);
          } catch (reason) {
            setError(
              reason instanceof Error ? reason.message : 'Open session restored, but roster failed to load.'
            );
          }
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Today's lectures could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    };
    void restore();
    return () => {
      active = false;
    };
  }, [loadNetwork, loadRoster, selectedLectureId, sessionKey]);

  // Live WebSocket for real-time check-in syncing
  useEffect(() => {
    if (!session || session.status === 'CLOSED') {
      setSocketStatus('disconnected');
      return;
    }
    // Vercel production calls the API through same-origin rewrites. Refresh
    // the roster over the authenticated API there; use WebSocket when an
    // explicit API origin is configured (local development).
    if (!apiBaseUrl) {
      setSocketStatus('polling');
      void loadRoster(session.id).catch(() => setSocketStatus('offline'));
      const timer = window.setInterval(() => {
        void loadRoster(session.id).catch(() => setSocketStatus('offline'));
      }, 4000);
      return () => window.clearInterval(timer);
    }
    const socketUrl = new URL(apiBaseUrl);
    socketUrl.protocol = socketUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    socketUrl.pathname = `/ws/attendance/${session.id}`;
    socketUrl.search = '';
    let socket: WebSocket | undefined;
    let retryTimer: number | undefined;
    let retries = 0;
    let stopped = false;

    const connect = () => {
      if (stopped) return;
      setSocketStatus('connecting');
      try {
        socket = new WebSocket(socketUrl);
      } catch {
        setSocketStatus('offline');
        retryTimer = window.setTimeout(connect, Math.min(1000 * 2 ** retries++, 30_000));
        return;
      }
      socket.onopen = () => {
        retries = 0;
        setSocketStatus('live');
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as { type?: string };
          if (payload.type === 'SESSION_STARTED' || payload.type === 'ATTENDANCE_RECORDED') {
            void loadRoster(session.id);
            addToast({
              type: 'info',
              message: 'Attendance record updated from live check-in.',
            });
          }
          if (payload.type === 'SESSION_CLOSED') {
            window.sessionStorage.removeItem(sessionKey);
            setSession((current) => (current ? { ...current, status: 'CLOSED' } : current));
            void loadRoster(session.id);
          }
        } catch {
          // ignore unreadable message
        }
      };
      socket.onerror = () => setSocketStatus('offline');
      socket.onclose = () => {
        if (stopped) return;
        setSocketStatus('offline');
        const delay = Math.min(1000 * 2 ** retries, 30_000);
        retries += 1;
        retryTimer = window.setTimeout(connect, delay);
      };
    };
    connect();
    return () => {
      stopped = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [addToast, loadRoster, session?.id, session?.status, sessionKey]);

  const startSession = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const next = await api<Session>('/api/faculty/attendance/session', {
        method: 'POST',
        body: jsonBody({ lecture_id: lectureId }),
      });
      window.sessionStorage.setItem(sessionKey, next.id);
      setSelectedLectureId(null);
      setSession(next);
      void loadNetwork(next.id);
      await loadRoster(next.id);
      setMessage('Attendance session opened. Students can now check in via their device.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start attendance session.');
    } finally {
      setBusy(false);
    }
  };

  const saveMark = async (student: Roster, nextStatus?: string) => {
    if (!session) return;
    const currentEdit = edit[student.student_id];
    const statusToSave = nextStatus || currentEdit?.status || student.status || 'PRESENT';
    const reasonToSave = currentEdit?.reason?.trim() || student.reason || 'Manual entry';

    if (reasonToSave.length < 3) {
      setError('Please provide a reason of at least 3 characters.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      if (student.attendance_id) {
        await api(`/api/faculty/attendance/${student.attendance_id}`, {
          method: 'PATCH',
          body: jsonBody({ status: statusToSave, reason: reasonToSave }),
        });
      } else {
        await api('/api/faculty/attendance/manual', {
          method: 'POST',
          body: jsonBody({
            session_id: session.id,
            student_id: student.student_id,
            status: statusToSave,
            reason: reasonToSave,
          }),
        });
      }
      await loadRoster(session.id);
      setEdit((previous) => {
        const copy = { ...previous };
        delete copy[student.student_id];
        return copy;
      });
      addToast({ type: 'success', message: `${student.full_name} marked as ${statusToSave}.` });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Attendance could not be saved.');
    } finally {
      setBusy(false);
    }
  };

  const markAll = async (targetStatus: 'PRESENT' | 'ABSENT') => {
    if (!session) return;
    setBusy(true);
    setError('');
    try {
      let count = 0;
      for (const st of roster) {
        if (st.status !== targetStatus) {
          if (st.attendance_id) {
            await api(`/api/faculty/attendance/${st.attendance_id}`, {
              method: 'PATCH',
              body: jsonBody({ status: targetStatus, reason: `Batch mark ${targetStatus.toLowerCase()}` }),
            });
          } else {
            await api('/api/faculty/attendance/manual', {
              method: 'POST',
              body: jsonBody({
                session_id: session.id,
                student_id: st.student_id,
                status: targetStatus,
                reason: `Batch mark ${targetStatus.toLowerCase()}`,
              }),
            });
          }
          count++;
        }
      }
      await loadRoster(session.id);
      addToast({ type: 'success', message: `Marked ${count} student(s) as ${targetStatus}.` });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Batch marking failed.');
    } finally {
      setBusy(false);
    }
  };

  const closeSession = async () => {
    if (!session) return;
    setBusy(true);
    setError('');
    try {
      await api(`/api/faculty/attendance/session/${session.id}/close`, { method: 'POST' });
      window.sessionStorage.removeItem(sessionKey);
      setSession({ ...session, status: 'CLOSED' });
      await loadRoster(session.id);
      addToast({
        type: 'success',
        message: 'Attendance session closed. Unmarked students have been recorded as absent.',
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not close the attendance session.');
    } finally {
      setBusy(false);
    }
  };

  const chooseAnotherLecture = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const today = await api<Lecture[]>('/api/faculty/lectures/today');
      const scheduled = today.filter((item) => item.status === 'SCHEDULED');
      setLectures(scheduled);
      setLectureId(scheduled[0]?.id || '');
      setRoster([]);
      setEdit({});
      setSession(null);
      setMessage(scheduled.length ? 'Choose another scheduled lecture to begin its session.' : 'No other scheduled lectures available today.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not refresh today's lectures.");
    } finally {
      setBusy(false);
    }
  };

  const activeLectureInfo = () => {
    const activeId = session?.lecture_id || lectureId;
    const lecture = lectures.find((l) => l.id === activeId);
    if (!lecture) return null;
    const sched = schedule.find((s) => s.allocation_id === lecture.allocation_id);
    return { lecture, sched };
  };

  const currentInfo = activeLectureInfo();

  const filteredRoster = roster.filter(
    (st) =>
      st.full_name.toLowerCase().includes(search.toLowerCase()) ||
      st.institutional_id.toLowerCase().includes(search.toLowerCase())
  );

  const presentCount = roster.filter((r) => r.status === 'PRESENT' || r.status === 'LATE').length;
  const absentCount = roster.filter((r) => r.status === 'ABSENT').length;
  const unmarkedCount = roster.filter((r) => !r.status).length;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Faculty · Live Attendance</p>
          <h1 className="text-2xl font-semibold text-slate-900">Attendance Session & Roster</h1>
          <p className="mt-1 text-sm text-slate-600">
            Open a session for your class. Students can check in on their devices, and you can record manual entries with audit tracking.
          </p>
        </div>

        {session && session.status === 'OPEN' && (
          <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800">
            {socketStatus === 'live' || socketStatus === 'polling' ? <Wifi size={14} className="animate-pulse text-emerald-600" /> : <WifiOff size={14} className="text-amber-600" />}
            <span>{socketStatus === 'live' ? 'Live check-in sync active' : socketStatus === 'polling' ? 'Roster refreshes every 4 seconds' : 'Live sync connecting…'}</span>
          </div>
        )}
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {message && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}

      {loading ? (
        <p className="text-sm text-slate-500">Loading today’s assigned lectures and open sessions…</p>
      ) : !session ? (
        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Open Attendance Session</h2>
          <p className="mt-1 text-xs text-slate-500">
            Select a class from your schedule. Opening the session unlocks face check-in for enrolled students.
          </p>

          <label className="mt-4 block text-sm font-medium text-slate-700">
            Today’s scheduled lecture
            <select
              value={lectureId}
              onChange={(event) => setLectureId(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-slate-200 p-2.5 text-sm outline-none focus:border-primary"
              disabled={!lectures.length}
            >
              <option value="">{lectures.length ? 'Choose a lecture…' : 'No scheduled lectures available today'}</option>
              {lectures.map((item) => {
                const info = schedule.find((s) => s.allocation_id === item.allocation_id);
                const label = info ? `${info.course_code} · ${info.course_name} (${info.classroom_name || info.classroom_code})` : item.allocation_id.slice(0, 8);
                return (
                  <option key={item.id} value={item.id}>
                    {new Date(item.starts_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}–
                    {new Date(item.ends_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} · {label}
                  </option>
                );
              })}
            </select>
          </label>

          <button
            type="button"
            disabled={!lectureId || busy}
            onClick={() => void startSession()}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
          >
            <Play size={15} />
            {busy ? 'Opening session…' : 'Start Attendance Session'}
          </button>
        </section>
      ) : (
        <div className="space-y-5">
          {/* Active Session Info Bar */}
          <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold ${session.status === 'OPEN' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>
                  <span className={`h-2 w-2 rounded-full ${session.status === 'OPEN' ? 'bg-emerald-600 animate-pulse' : 'bg-slate-500'}`} />
                  {session.status === 'OPEN' ? 'Session OPEN' : 'Session CLOSED'}
                </span>
                {currentInfo?.sched && (
                  <span className="text-sm font-semibold text-slate-800">
                    {currentInfo.sched.course_code} · {currentInfo.sched.course_name}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {currentInfo?.sched ? `Classroom: ${currentInfo.sched.classroom_code}` : 'Live Class Roster'} · {roster.length} enrolled students
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {session.status === 'CLOSED' ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void chooseAnotherLecture()}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-50"
                >
                  <RotateCcw size={14} />
                  Choose another lecture
                </button>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void closeSession()}
                  className="inline-flex items-center gap-2 rounded-lg border border-rose-300 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
                >
                  <Square size={14} />
                  {busy ? 'Closing…' : 'Close Session & Save'}
                </button>
              )}
            </div>
          </section>

          {/* Dynamic Classroom Network & Wi-Fi Lock (Auto-detected from Faculty Device) */}
          {session.status === 'OPEN' && (
            <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sky-100 bg-gradient-to-r from-sky-50/80 to-indigo-50/80 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${networkStatus?.enforced ? 'bg-sky-600 text-white shadow-sm' : 'bg-amber-500 text-white'}`}>
                  <Wifi size={20} />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900">Classroom Wi-Fi Geofence:</span>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${networkStatus?.enforced ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-amber-100 text-amber-800 border border-amber-200'}`}>
                      {networkStatus?.enforced ? '🔒 Locked to Room Network' : '⚡ Demo Mode (Bypassed)'}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-600">
                    Bound Subnet: <code className="rounded bg-white/90 px-1.5 py-0.5 font-mono text-xs font-semibold text-sky-950 border border-slate-200">{networkStatus?.bound_subnet || 'Detecting…'}</code>
                    <span className="ml-2 text-slate-500">(Faculty Device IP: {networkStatus?.detected_ip || '…'})</span>
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleToggleEnforcement()}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition shadow-sm ${networkStatus?.enforced ? 'border border-amber-300 bg-white text-amber-900 hover:bg-amber-50' : 'bg-sky-600 text-white hover:bg-sky-700'}`}
                >
                  {networkStatus?.enforced ? 'Switch to Demo Mode (Allow All)' : 'Enforce Wi-Fi Match'}
                </button>
                <button
                  type="button"
                  onClick={() => void handleRedetectNetwork()}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm"
                  title="Re-detect IP and subnet from this device"
                >
                  🔄 Re-detect My Network
                </button>
              </div>
            </section>
          )}

          {/* Quick Metrics Bar */}
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border bg-white p-3 text-center">
              <span className="text-xs text-slate-500">Enrolled</span>
              <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">{roster.length}</p>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-3 text-center">
              <span className="text-xs font-medium text-emerald-800">Present</span>
              <p className="mt-1 font-mono text-2xl font-semibold text-emerald-700">{presentCount}</p>
            </div>
            <div className="rounded-xl border border-rose-100 bg-rose-50/50 p-3 text-center">
              <span className="text-xs font-medium text-rose-800">Absent</span>
              <p className="mt-1 font-mono text-2xl font-semibold text-rose-700">{absentCount}</p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-3 text-center">
              <span className="text-xs font-medium text-amber-800">Unmarked</span>
              <p className="mt-1 font-mono text-2xl font-semibold text-amber-700">{unmarkedCount}</p>
            </div>
          </section>

          {/* Roster Table Card */}
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
              <div className="relative min-w-[240px] flex-1 max-w-sm">
                <Search size={16} className="absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search student by name or ID…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-1.5 text-xs outline-none focus:border-primary"
                />
              </div>

              {session.status === 'OPEN' && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void markAll('PRESENT')}
                    className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
                  >
                    <CheckCircle2 size={13} /> Mark All Present
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void markAll('ABSENT')}
                    className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-800 hover:bg-rose-100 disabled:opacity-50"
                  >
                    <XCircle size={13} /> Mark All Absent
                  </button>
                </div>
              )}
            </div>

            {filteredRoster.length ? (
              <div className="divide-y divide-slate-100">
                {filteredRoster.map((student) => {
                  const currentStatus = edit[student.student_id]?.status || student.status;
                  const currentReason = edit[student.student_id]?.reason ?? (student.reason || '');

                  return (
                    <article
                      key={student.student_id}
                      className="flex flex-wrap items-center justify-between gap-4 p-4 transition hover:bg-slate-50/60"
                    >
                      <div className="min-w-[180px]">
                        <span className="block text-sm font-semibold text-slate-900">{student.full_name}</span>
                        <span className="font-mono text-xs text-slate-500">{student.institutional_id}</span>
                        {student.source && (
                          <span className="ml-2 inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 uppercase font-semibold">
                            {student.source === 'VISION' ? 'Face self check-in' : student.source}
                          </span>
                        )}
                      </div>

                      {session.status === 'OPEN' ? (
                        <div className="flex flex-wrap items-center gap-2">
                          {/* 1-click pills */}
                          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5">
                            {(['PRESENT', 'LATE', 'ABSENT', 'EXCUSED'] as const).map((st) => (
                              <button
                                key={st}
                                type="button"
                                onClick={() => {
                                  setEdit({
                                    ...edit,
                                    [student.student_id]: {
                                      status: st,
                                      reason: currentReason || `Marked ${st.toLowerCase()}`,
                                    },
                                  });
                                  void saveMark(student, st);
                                }}
                                className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                                  currentStatus === st
                                    ? st === 'PRESENT'
                                      ? 'bg-emerald-600 text-white shadow-sm'
                                      : st === 'LATE'
                                      ? 'bg-amber-600 text-white shadow-sm'
                                      : st === 'ABSENT'
                                      ? 'bg-rose-600 text-white shadow-sm'
                                      : 'bg-indigo-600 text-white shadow-sm'
                                    : 'text-slate-600 hover:text-slate-900'
                                }`}
                              >
                                {st}
                              </button>
                            ))}
                          </div>

                          <input
                            type="text"
                            placeholder="Reason (optional)"
                            value={currentReason}
                            onChange={(e) =>
                              setEdit({
                                ...edit,
                                [student.student_id]: {
                                  status: currentStatus || 'PRESENT',
                                  reason: e.target.value,
                                },
                              })
                            }
                            className="w-40 rounded-lg border border-slate-200 px-2.5 py-1 text-xs outline-none focus:border-primary"
                          />

                          {edit[student.student_id] && (
                            <button
                              type="button"
                              onClick={() => void saveMark(student)}
                              disabled={busy}
                              className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-primary-dark disabled:opacity-40"
                            >
                              <Check size={13} /> Save
                            </button>
                          )}
                        </div>
                      ) : (
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-bold ${
                            student.status === 'PRESENT'
                              ? 'bg-emerald-100 text-emerald-800'
                              : student.status === 'LATE'
                              ? 'bg-amber-100 text-amber-800'
                              : student.status === 'ABSENT'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {student.status || 'UNMARKED'}
                        </span>
                      )}
                    </article>
                  );
                })}
              </div>
            ) : (
              <p className="p-8 text-center text-sm text-slate-500">
                {search ? 'No students match your search criteria.' : 'Roster is empty or unavailable.'}
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
};
