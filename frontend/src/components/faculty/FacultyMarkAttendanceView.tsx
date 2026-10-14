import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, Check, ClipboardCheck, Play, Square, Video } from 'lucide-react';
import { api, apiBaseUrl, jsonBody } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Lecture = { id: string; allocation_id: string; starts_at: string; ends_at: string; status: string };
type Session = { id: string; lecture_id: string; status: string };
type Roster = { student_id: string; institutional_id: string; full_name: string; attendance_id: string | null; status: string | null; source: string | null; reason: string | null };
type Recognition = { state: string; attendance_state?: string | null; student_id?: string | null; message?: string | null };
type CameraState = 'off' | 'active' | 'denied' | 'unavailable' | 'error';
type SocketState = 'disconnected' | 'connecting' | 'live' | 'offline';
type TimetableItem = { allocation_id: string; weekday: number; starts_at: string; ends_at: string; course_code: string; course_name: string; classroom_code: string; classroom_name: string };

export const FacultyMarkAttendanceView: React.FC<{ mode?: 'camera' | 'manual' }> = ({ mode = 'camera' }) => {
  const { addToast, currentUser, selectedLectureId, setCurrentRoute, setSelectedLectureId } = useApp();
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
  const [camera, setCamera] = useState<CameraState>('off');
  const [recognition, setRecognition] = useState<Recognition | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketState>('disconnected');
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const manual = mode === 'manual';
  const sessionKey = `ams-open-attendance-session:${currentUser.id}`;

  const stopCamera = useCallback(() => {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
    setCamera('off');
  }, []);

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
        if (savedId) {
          let restored: Session | null = null;
          try {
            restored = await api<Session>(`/api/faculty/attendance/session/${encodeURIComponent(savedId)}`);
          } catch {
            window.sessionStorage.removeItem(sessionKey);
          }
          if (!active) return;
          if (restored?.status === 'OPEN') {
            setSession(restored);
            try { await loadRoster(restored.id); }
            catch (reason) { setError(reason instanceof Error ? reason.message : 'Open session restored, but its roster could not be loaded.'); }
          } else if (restored) {
            window.sessionStorage.removeItem(sessionKey);
          }
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : 'Today’s lectures could not be loaded.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void restore();
    return () => {
      active = false;
      stream.current?.getTracks().forEach((track) => track.stop());
      stream.current = null;
    };
  }, [loadRoster, selectedLectureId, sessionKey]);

  useEffect(() => {
    if (camera !== 'active' || !video.current || !stream.current) return;
    video.current.srcObject = stream.current;
    void video.current.play().catch(() => {
      stream.current?.getTracks().forEach((track) => track.stop());
      stream.current = null;
      setError('The camera is available, but video playback could not start. Check browser playback permissions and retry.');
      setCamera('error');
    });
  }, [camera]);

  useEffect(() => {
    if (!session || session.status === 'CLOSED') {
      setSocketStatus('disconnected');
      return;
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
      socket.onopen = () => { retries = 0; setSocketStatus('live'); };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as { type?: string };
          if (payload.type === 'SESSION_STARTED' || payload.type === 'ATTENDANCE_RECORDED') {
            void loadRoster(session.id).catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not refresh attendance roster.'));
          }
          if (payload.type === 'SESSION_CLOSED') {
            stopCamera();
            window.sessionStorage.removeItem(sessionKey);
            setSession((current) => current ? { ...current, status: 'CLOSED' } : current);
            void loadRoster(session.id).catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not refresh attendance roster.'));
          }
        } catch {
          setError('Received an unreadable live attendance update.');
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
  }, [loadRoster, session?.id, session?.status, sessionKey, stopCamera]);

  const startSession = async () => {
    setBusy(true); setError(''); setMessage('');
    try {
      const next = await api<Session>('/api/faculty/attendance/session', { method: 'POST', body: jsonBody({ lecture_id: lectureId }) });
      window.sessionStorage.setItem(sessionKey, next.id);
      setSelectedLectureId(null);
      setSession(next);
      await loadRoster(next.id);
      setMessage('Attendance session opened. It will be restored if you switch views or refresh this tab.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start the attendance session.');
    } finally { setBusy(false); }
  };

  const startCamera = async () => {
    setError('');
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setCamera('unavailable');
      setError('Camera access requires HTTPS or localhost and a browser that supports camera capture. You can switch to manual attendance.');
      return;
    }
    try {
      const input = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
      stream.current = input;
      setCamera('active');
    } catch (reason) {
      const name = reason instanceof DOMException ? reason.name : '';
      if (name === 'NotAllowedError' || name === 'SecurityError') setCamera('denied');
      else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') setCamera('unavailable');
      else setCamera('error');
    }
  };

  const recognize = async () => {
    if (!session || !video.current || camera !== 'active') return;
    if (video.current.videoWidth < 1 || video.current.videoHeight < 1) {
      setError('The camera has not produced a frame yet. Wait a moment and retry.');
      return;
    }
    setBusy(true); setError(''); setRecognition(null);
    try {
      const canvas = document.createElement('canvas');
      canvas.width = video.current.videoWidth;
      canvas.height = video.current.videoHeight;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('This browser could not prepare a camera frame.');
      context.drawImage(video.current, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
      if (!blob) throw new Error('Could not capture a camera frame.');
      const form = new FormData();
      form.append('image', blob, 'attendance-frame.jpg');
      const result = await api<Recognition>(`/api/faculty/attendance/session/${session.id}/recognize`, { method: 'POST', body: form });
      setRecognition(result);
      await loadRoster(session.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Recognition request failed.');
    } finally { setBusy(false); }
  };

  const saveMark = async (student: Roster) => {
    const update = edit[student.student_id];
    if (!session || !update) return;
    if (update.reason.trim().length < 5) { setError('A reason of at least 5 characters is required.'); return; }
    setBusy(true); setError('');
    try {
      if (student.attendance_id) {
        await api(`/api/faculty/attendance/${student.attendance_id}`, { method: 'PATCH', body: jsonBody({ status: update.status, reason: update.reason.trim() }) });
      } else {
        await api('/api/faculty/attendance/manual', { method: 'POST', body: jsonBody({ session_id: session.id, student_id: student.student_id, status: update.status, reason: update.reason.trim() }) });
      }
      await loadRoster(session.id);
      setEdit((previous) => { const next = { ...previous }; delete next[student.student_id]; return next; });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Attendance could not be saved.');
    } finally { setBusy(false); }
  };

  const closeSession = async () => {
    if (!session) return;
    setBusy(true); setError('');
    try {
      await api(`/api/faculty/attendance/session/${session.id}/close`, { method: 'POST' });
      window.sessionStorage.removeItem(sessionKey);
      setSession({ ...session, status: 'CLOSED' });
      stopCamera();
      await loadRoster(session.id);
      addToast({ type: 'success', message: 'Attendance session closed; unmarked students were recorded absent.' });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not close the attendance session.');
    } finally { setBusy(false); }
  };

  const chooseAnotherLecture = async () => {
    setBusy(true); setError(''); setMessage('');
    try {
      const today = await api<Lecture[]>('/api/faculty/lectures/today');
      const scheduled = today.filter((item) => item.status === 'SCHEDULED');
      setLectures(scheduled);
      setLectureId(scheduled[0]?.id || '');
      setRoster([]); setEdit({}); setRecognition(null); setSession(null);
      setMessage(scheduled.length ? 'Choose another scheduled lecture to begin its attendance session.' : 'No other scheduled lectures are available today.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not refresh today’s lectures.');
    } finally { setBusy(false); }
  };

  const recognitionLabel = (result: Recognition) => {
    if (result.message) return result.message;
    const labels: Record<string, string> = { recognized: 'Face recognized', unknown: 'No enrolled face matched this frame', multiple_faces: 'Show one face at a time', low_confidence: 'Match confidence was too low; use manual attendance', error: 'Recognition service is unavailable' };
    return labels[result.state] || `Recognition state: ${result.state}`;
  };

  return <div className="mx-auto w-full max-w-6xl space-y-5">
    <header className="flex flex-wrap items-end justify-between gap-3"><div><p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Faculty · live API</p><h1 className="text-2xl font-semibold text-slate-900">{manual ? 'Manual attendance' : 'Camera attendance'}</h1><p className="mt-1 text-sm text-slate-600">Attendance is scoped to your assigned lecture and saved with an audit record.</p></div>
      <button type="button" onClick={() => { stopCamera(); setCurrentRoute(manual ? 'camera-attendance-session' : 'faculty-manual-attendance'); }} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">{manual ? <Camera size={16}/> : <ClipboardCheck size={16}/>} {manual ? 'Camera mode' : 'Manual mode'}</button>
    </header>
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {message && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
    {loading ? <p className="text-sm text-slate-500">Loading today’s assigned lectures and any open session…</p> : !session ? <section className="rounded-2xl border bg-white p-5"><h2 className="text-sm font-semibold">Open attendance session</h2><label className="mt-4 block text-sm font-medium">Today’s scheduled lecture<select value={lectureId} onChange={(event) => setLectureId(event.target.value)} className="mt-1.5 w-full rounded-lg border p-2.5" disabled={!lectures.length}><option value="">{lectures.length ? 'Choose lecture' : 'No scheduled lectures available today'}</option>{lectures.map((item) => { const info = schedule.find((s) => s.allocation_id === item.allocation_id); const label = info ? `${info.course_code} · ${info.course_name}` : item.allocation_id.slice(0, 8); return <option key={item.id} value={item.id}>{new Date(item.starts_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}–{new Date(item.ends_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} · {label}</option>; })}</select></label><button type="button" disabled={!lectureId || busy} onClick={() => void startSession()} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"><Play size={15}/>{busy ? 'Opening…' : 'Start session'}</button></section> : <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
      {!manual && session.status !== 'CLOSED' && <section className="space-y-3 rounded-2xl border bg-white p-4"><div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Camera recognition</h2><span role="status" aria-live="polite" className="text-xs text-slate-500">{camera === 'active' ? 'Camera active' : camera === 'denied' ? 'Permission denied' : camera === 'unavailable' ? 'Camera unavailable' : camera === 'error' ? 'Camera error' : 'Camera off'}</span></div>
        <div className="relative aspect-video overflow-hidden rounded-xl bg-slate-900">{camera === 'active' ? <video ref={video} muted playsInline aria-label="Live camera preview" className="h-full w-full object-cover"/> : <div className="grid h-full place-items-center px-4 text-center text-sm text-white"><span><CameraOff className="mx-auto mb-2"/>{camera === 'denied' ? 'Camera permission denied. Allow camera access in your browser settings, or switch to manual attendance.' : camera === 'unavailable' ? 'No supported camera is available. You can continue with manual attendance.' : camera === 'error' ? 'Camera could not start. Stop any other application using it and retry.' : 'Camera stays off until you choose Start camera.'}</span></div>}</div>
        <div className="flex flex-wrap gap-2">{camera !== 'active' ? <button type="button" onClick={() => void startCamera()} disabled={busy || session.status === 'CLOSED'} className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Start camera</button> : <button type="button" onClick={() => void recognize()} disabled={busy || session.status === 'CLOSED'} className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"><Video className="mr-1 inline" size={15}/>{busy ? 'Processing…' : 'Capture & recognize'}</button>}<button type="button" disabled={camera === 'off'} onClick={stopCamera} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-50">Stop camera</button></div>
        {recognition && <p role="status" aria-live="polite" className="rounded-lg bg-stone-50 p-3 text-sm">{recognitionLabel(recognition)}{recognition.attendance_state ? ` · ${recognition.attendance_state}` : ''}</p>}
      </section>}
      <section className="rounded-2xl border bg-white"><div className="flex flex-wrap items-center justify-between gap-3 border-b p-4"><div><h2 className="text-sm font-semibold">{session.status === 'CLOSED' ? 'Attendance session closed' : 'Enrolled roster'}</h2><p className="mt-1 text-xs text-slate-500">{roster.length} students · present {roster.filter((row) => row.status === 'PRESENT' || row.status === 'LATE').length} · absent {roster.filter((row) => row.status === 'ABSENT').length}</p><p role="status" aria-live="polite" className="mt-1 text-xs text-slate-500">Live attendance updates: {socketStatus}</p></div>{session.status === 'CLOSED' ? <button type="button" disabled={busy} onClick={() => void chooseAnotherLecture()} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Choose another lecture</button> : <button type="button" disabled={busy} onClick={() => void closeSession()} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm disabled:opacity-50"><Square size={14}/>{busy ? 'Saving…' : 'Close session'}</button>}</div>
        {roster.length ? <ul className="divide-y">{roster.map((student) => <li key={student.student_id} className="space-y-2 p-4"><div className="flex items-center justify-between gap-3"><span><span className="block text-sm font-medium">{student.full_name}</span><span className="font-mono text-xs text-slate-500">{student.institutional_id}</span></span><span className="text-xs font-semibold">{student.status || 'UNMARKED'}</span></div>{session.status !== 'CLOSED' && <div className="grid gap-2 sm:grid-cols-[130px_1fr_auto]"><select aria-label={`Attendance status for ${student.full_name}`} value={edit[student.student_id]?.status || student.status || 'PRESENT'} onChange={(event) => setEdit({ ...edit, [student.student_id]: { status: event.target.value, reason: edit[student.student_id]?.reason || '' } })} className="rounded-lg border px-2 py-2 text-xs"><option value="PRESENT">Present</option><option value="LATE">Late</option><option value="ABSENT">Absent</option><option value="EXCUSED">Excused</option></select><input aria-label={`Reason for ${student.full_name}`} value={edit[student.student_id]?.reason || ''} onChange={(event) => setEdit({ ...edit, [student.student_id]: { status: edit[student.student_id]?.status || student.status || 'PRESENT', reason: event.target.value } })} placeholder="Reason (required, 5+ characters)" className="rounded-lg border px-3 py-2 text-xs"/><button type="button" onClick={() => void saveMark(student)} disabled={busy || !edit[student.student_id]} className="inline-flex items-center justify-center gap-1 rounded-lg border px-3 py-2 text-xs font-semibold disabled:opacity-40"><Check size={14}/>Save</button></div>}</li>)}</ul> : <p className="p-6 text-sm text-slate-500">Roster is empty or unavailable.</p>}
      </section>
    </div>}
  </div>;
};
