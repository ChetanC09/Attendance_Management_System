import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Download, FileSpreadsheet, Upload } from 'lucide-react';
import { api, jsonBody } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Entry = { id: string; allocation_id: string; weekday: number; starts_at: string; ends_at: string };
type Allocation = { id: string; course_id: string; section_id: string; faculty_id: string; is_active: boolean };
type Course = { id: string; code: string; name: string };
type Section = { id: string; name: string };
type Lecture = {
  id: string;
  allocation_id: string;
  timetable_entry_id: string | null;
  classroom_id: string;
  starts_at: string;
  ends_at: string;
  status: string;
  cancellation_reason: string | null;
};

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const AdminLectureOperations: React.FC = () => {
  const { addToast } = useApp();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [classroom, setClassroom] = useState('');
  const [rooms, setRooms] = useState<{ id: string; code: string; name: string }[]>([]);
  const [selectedEntry, setSelectedEntry] = useState('');
  const [through, setThrough] = useState('');
  const [selectedLecture, setSelectedLecture] = useState<Lecture | null>(null);
  const [reason, setReason] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  // Timetable CSV Import state
  const [csvText, setCsvText] = useState('');
  const [importThrough, setImportThrough] = useState('');
  const [importResult, setImportResult] = useState<{
    imported_entries: number;
    generated_lectures: number;
    errors: { row: number; error: string }[];
  } | null>(null);

  const load = () =>
    api<Lecture[]>('/api/admin/lectures?starts_after=2020-01-01T00:00:00Z').then(setLectures);

  const refreshAll = () =>
    Promise.all([
      api<Entry[]>('/api/admin/timetable'),
      api<{ id: string; code: string; name: string }[]>('/api/admin/classrooms'),
      api<Allocation[]>('/api/admin/allocations'),
      api<Course[]>('/api/admin/courses'),
      api<Section[]>('/api/admin/sections'),
      load(),
    ]).then(([list, classrooms, allocs, courseList, sectionList]) => {
      setEntries(list);
      if (!selectedEntry && list[0]) setSelectedEntry(list[0].id);
      setRooms(classrooms);
      if (!classroom && classrooms[0]) setClassroom(classrooms[0].id);
      setAllocations(allocs);
      setCourses(courseList);
      setSections(sectionList);
    });

  useEffect(() => {
    refreshAll().catch((e) => setError(e instanceof Error ? e.message : 'Could not load timetable data.'));
  }, []);

  const entryLabel = (entry: Entry) => {
    const alloc = allocations.find((a) => a.id === entry.allocation_id);
    const course = alloc ? courses.find((c) => c.id === alloc.course_id) : null;
    const section = alloc ? sections.find((s) => s.id === alloc.section_id) : null;
    const time = `${entry.starts_at.slice(0, 5)}–${entry.ends_at.slice(0, 5)}`;
    const day = DAYS[entry.weekday] ?? `Day ${entry.weekday}`;
    const label = course ? `${course.code} · ${course.name}` : entry.allocation_id.slice(0, 8);
    const sectionLabel = section ? ` · ${section.name}` : '';
    return `${day} ${time} · ${label}${sectionLabel}`;
  };

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await api<{ created_count: number }>(
        `/api/admin/timetable/${selectedEntry}/generate?through=${through}`,
        { method: 'POST' }
      );
      setMessage(`${result.created_count} lectures generated.`);
      addToast({ type: 'success', message: `Generated ${result.created_count} lecture records.` });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Lecture generation failed.');
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!selectedLecture) return;
    if (reason.trim().length < 5) {
      setError('A cancellation reason of at least 5 characters is required.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api(`/api/admin/lectures/${selectedLecture.id}/cancel`, {
        method: 'POST',
        body: jsonBody({ reason }),
      });
      setSelectedLecture(null);
      setReason('');
      addToast({ type: 'info', message: 'Lecture cancelled.' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cancellation failed.');
    } finally {
      setBusy(false);
    }
  };

  const reschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLecture) return;
    setBusy(true);
    setError('');
    try {
      await api(`/api/admin/lectures/${selectedLecture.id}/reschedule`, {
        method: 'PATCH',
        body: jsonBody({
          starts_at: new Date(start).toISOString(),
          ends_at: new Date(end).toISOString(),
          classroom_id: classroom,
        }),
      });
      setSelectedLecture(null);
      addToast({ type: 'success', message: 'Lecture rescheduled.' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reschedule failed.');
    } finally {
      setBusy(false);
    }
  };

  const downloadCsvTemplate = () => {
    const sampleCourse = courses[0]?.code || 'CS101';
    const sampleSection = sections[0]?.name || 'A';
    const sampleRoom = rooms[0]?.code || 'LH-101';
    const todayStr = new Date().toISOString().split('T')[0];

    const templateContent =
      `course_code,section_name,classroom_code,weekday,starts_at,ends_at,effective_from,effective_until\n` +
      `${sampleCourse},${sampleSection},${sampleRoom},Mon,09:00,10:00,${todayStr},2026-12-31\n` +
      `${sampleCourse},${sampleSection},${sampleRoom},Wed,11:00,12:00,${todayStr},2026-12-31\n` +
      `${sampleCourse},${sampleSection},${sampleRoom},Fri,14:00,15:00,${todayStr},2026-12-31\n`;

    const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'timetable_template.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setCsvText(evt.target?.result as string || '');
    };
    reader.readAsText(file);
  };

  const importTimetable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvText.trim()) return;
    setBusy(true);
    setError('');
    setMessage('');
    setImportResult(null);
    try {
      const res = await api<{
        imported_entries: number;
        generated_lectures: number;
        errors: { row: number; error: string }[];
      }>('/api/admin/timetable/import', {
        method: 'POST',
        body: jsonBody({
          csv: csvText,
          generate_through: importThrough || null,
        }),
      });
      setImportResult(res);
      if (res.imported_entries > 0) {
        addToast({
          type: 'success',
          message: `Successfully imported ${res.imported_entries} timetable entries (${res.generated_lectures} lectures generated).`,
        });
        await refreshAll();
      } else if (res.errors.length) {
        addToast({
          type: 'error',
          message: `Import encountered errors on ${res.errors.length} row(s).`,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Timetable import failed.');
    } finally {
      setBusy(false);
    }
  };

  const lectureAllocationLabel = (lecture: Lecture) => {
    const alloc = allocations.find((a) => a.id === lecture.allocation_id);
    const course = alloc ? courses.find((c) => c.id === alloc.course_id) : null;
    return course ? `${course.code} · ${course.name}` : lecture.allocation_id.slice(0, 8);
  };

  return (
    <div className="mt-6 space-y-6">
      {/* ── Timetable Import Section ─────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <FileSpreadsheet size={18} className="text-primary-dark" />
              Import Timetable Schedule (CSV / Template)
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Bulk-upload recurring lecture schedules matching course code, section, room, weekday, and times.
            </p>
          </div>
          <button
            type="button"
            onClick={downloadCsvTemplate}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
          >
            <Download size={13} />
            Download CSV Template
          </button>
        </div>

        <form onSubmit={importTimetable} className="mt-4 space-y-4">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
              <span>Paste CSV content or upload a file:</span>
              <label className="cursor-pointer font-semibold text-primary hover:underline inline-flex items-center gap-1">
                <Upload size={12} />
                Upload .csv file
                <input type="file" accept=".csv,text/csv" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>
            <textarea
              required
              rows={5}
              placeholder="course_code,section_name,classroom_code,weekday,starts_at,ends_at,effective_from,effective_until&#10;CS101,A,LH-101,Mon,09:00,10:00,2026-08-01,2026-12-31"
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              className="w-full rounded-xl border border-slate-200 p-3 font-mono text-xs outline-none focus:border-primary"
            />
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs font-medium text-slate-700">
              Optional: Auto-generate dated lectures through
              <input
                type="date"
                value={importThrough}
                onChange={(e) => setImportThrough(e.target.value)}
                className="mt-1 block rounded-lg border border-slate-200 p-2 text-xs outline-none focus:border-primary"
              />
            </label>

            <button
              disabled={busy || !csvText.trim()}
              className="rounded-lg bg-primary px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
            >
              {busy ? 'Importing…' : 'Import Schedule Entries'}
            </button>
          </div>
        </form>

        {importResult && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1 font-semibold text-emerald-800">
                <CheckCircle2 size={15} /> {importResult.imported_entries} entries imported
              </span>
              {importResult.generated_lectures > 0 && (
                <span className="font-semibold text-slate-700">
                  · {importResult.generated_lectures} lectures generated
                </span>
              )}
              {importResult.errors.length > 0 && (
                <span className="flex items-center gap-1 font-semibold text-rose-700">
                  <AlertCircle size={15} /> {importResult.errors.length} row error(s)
                </span>
              )}
            </div>

            {importResult.errors.length > 0 && (
              <ul className="mt-2.5 space-y-1 text-xs text-rose-700">
                {importResult.errors.map((err, idx) => (
                  <li key={idx}>
                    Row {err.row}: {err.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* ── Generate Lectures from Existing Entry ────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Generate dated lectures from timetable entry</h2>
        <p className="mt-1 text-xs text-slate-500">
          Creates scheduled lecture instances for an existing recurring timetable entry across the semester.
        </p>
        <form onSubmit={generate} className="mt-4 grid min-w-0 gap-3 sm:grid-cols-[minmax(0,1fr)_200px_auto]">
          <select
            required
            value={selectedEntry}
            onChange={(e) => setSelectedEntry(e.target.value)}
            className="min-w-0 rounded-lg border border-slate-200 p-2 text-sm outline-none focus:border-primary"
          >
            <option value="">{entries.length ? 'Choose timetable entry…' : 'No entries available'}</option>
            {entries.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entryLabel(entry)}
              </option>
            ))}
          </select>
          <input
            required
            type="date"
            value={through}
            onChange={(e) => setThrough(e.target.value)}
            className="rounded-lg border border-slate-200 p-2 text-sm outline-none focus:border-primary"
          />
          <button
            disabled={busy || !selectedEntry || !through}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
          >
            {busy ? 'Generating…' : 'Generate'}
          </button>
        </form>
      </section>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {message && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}

      {/* ── Dated Lectures List ──────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-slate-100 p-5">
          <h2 className="text-sm font-semibold text-slate-900">Scheduled Lectures Catalogue ({lectures.length})</h2>
        </div>
        {lectures.length ? (
          <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
            {lectures.map((item) => (
              <article key={item.id} className="flex flex-wrap items-center justify-between gap-3 p-4 transition hover:bg-slate-50/60">
                <div>
                  <span className="block text-sm font-medium text-slate-900">
                    {new Date(item.starts_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })} ·{' '}
                    <span className={`font-semibold ${item.status === 'SCHEDULED' ? 'text-primary' : item.status === 'CONDUCTED' ? 'text-emerald-700' : 'text-slate-500'}`}>
                      {item.status}
                    </span>
                    <span className="ml-2 text-xs font-normal text-slate-500">{lectureAllocationLabel(item)}</span>
                  </span>
                  <span className="font-mono text-[11px] text-slate-400">{item.id}</span>
                  {item.cancellation_reason && (
                    <span className="block text-xs text-rose-700">Reason: {item.cancellation_reason}</span>
                  )}
                </div>
                {item.status === 'SCHEDULED' && (
                  <button
                    onClick={() => {
                      setSelectedLecture(item);
                      setStart(item.starts_at.slice(0, 16));
                      setEnd(item.ends_at.slice(0, 16));
                    }}
                    className="text-xs font-semibold text-primary hover:underline"
                  >
                    Reschedule / Cancel
                  </button>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="p-6 text-sm text-slate-500">No generated lectures found.</p>
        )}
      </section>

      {/* ── Reschedule / Cancel Modal ────────────────────────────── */}
      {selectedLecture && (
        <section className="grid gap-5 rounded-2xl border border-primary/30 bg-white p-5 shadow-sm md:grid-cols-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void cancel();
            }}
            className="space-y-3"
          >
            <h3 className="text-sm font-semibold text-slate-900">Cancel lecture</h3>
            <p className="text-xs text-slate-600">
              {lectureAllocationLabel(selectedLecture)} · {new Date(selectedLecture.starts_at).toLocaleString()}
            </p>
            <label className="block text-xs font-medium text-slate-700">
              Reason (5–500 characters)
              <textarea
                required
                minLength={5}
                maxLength={500}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2.5 text-xs outline-none focus:border-primary"
              />
            </label>
            <div className="flex gap-2">
              <button
                disabled={busy}
                className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800 transition hover:bg-rose-100 disabled:opacity-50"
              >
                Cancel lecture
              </button>
              <button
                type="button"
                onClick={() => setSelectedLecture(null)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </form>

          <form onSubmit={reschedule} className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Reschedule lecture</h3>
            <label className="block text-xs font-medium text-slate-700">
              Starts at
              <input
                required
                type="datetime-local"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2 text-xs outline-none focus:border-primary"
              />
            </label>
            <label className="block text-xs font-medium text-slate-700">
              Ends at
              <input
                required
                type="datetime-local"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2 text-xs outline-none focus:border-primary"
              />
            </label>
            <label className="block text-xs font-medium text-slate-700">
              Classroom
              <select
                value={classroom}
                onChange={(e) => setClassroom(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-200 p-2 text-xs outline-none focus:border-primary"
              >
                {rooms.map((room) => (
                  <option key={room.id} value={room.id}>
                    {room.code} · {room.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex gap-2">
              <button
                disabled={busy}
                className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
              >
                Save new schedule
              </button>
              <button
                type="button"
                onClick={() => setSelectedLecture(null)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
};
