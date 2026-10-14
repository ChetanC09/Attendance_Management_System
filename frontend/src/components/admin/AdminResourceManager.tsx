import React, { useEffect, useMemo, useState } from 'react';
import { api, jsonBody } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Field = {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'date' | 'time' | 'uuid' | 'boolean';
  required?: boolean;
  min?: number;
  max?: number;
};

type ResourceConfig = { title: string; path: string; create: Field[]; update: Field[] };

const resources: Record<string, ResourceConfig> = {
  'admin-departments': {
    title: 'Departments',
    path: 'departments',
    create: [
      { key: 'code', label: 'Code', required: true },
      { key: 'name', label: 'Name', required: true },
    ],
    update: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-academic-years': {
    title: 'Academic years',
    path: 'academic-years',
    create: [
      { key: 'name', label: 'Name', required: true },
      { key: 'starts_on', label: 'Starts on', type: 'date', required: true },
      { key: 'ends_on', label: 'Ends on', type: 'date', required: true },
    ],
    update: [
      { key: 'name', label: 'Name' },
      { key: 'starts_on', label: 'Starts on', type: 'date' },
      { key: 'ends_on', label: 'Ends on', type: 'date' },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-semesters': {
    title: 'Semesters',
    path: 'semesters',
    create: [
      { key: 'academic_year_id', label: 'Academic year', type: 'uuid', required: true },
      { key: 'number', label: 'Semester number', type: 'number', required: true, min: 1, max: 12 },
      { key: 'starts_on', label: 'Starts on', type: 'date', required: true },
      { key: 'ends_on', label: 'Ends on', type: 'date', required: true },
    ],
    update: [
      { key: 'number', label: 'Semester number', type: 'number' },
      { key: 'starts_on', label: 'Starts on', type: 'date' },
      { key: 'ends_on', label: 'Ends on', type: 'date' },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-sections': {
    title: 'Sections',
    path: 'sections',
    create: [
      { key: 'department_id', label: 'Department', type: 'uuid', required: true },
      { key: 'academic_year_id', label: 'Academic year', type: 'uuid', required: true },
      { key: 'name', label: 'Name', required: true },
    ],
    update: [
      { key: 'name', label: 'Name' },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-courses': {
    title: 'Courses',
    path: 'courses',
    create: [
      { key: 'department_id', label: 'Department', type: 'uuid', required: true },
      { key: 'code', label: 'Code', required: true },
      { key: 'name', label: 'Name', required: true },
      { key: 'credits', label: 'Credits', type: 'number', min: 0, max: 30 },
    ],
    update: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'credits', label: 'Credits', type: 'number', min: 0, max: 30 },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-classrooms': {
    title: 'Classrooms',
    path: 'classrooms',
    create: [
      { key: 'code', label: 'Code', required: true },
      { key: 'name', label: 'Name', required: true },
      { key: 'capacity', label: 'Capacity', type: 'number', min: 1 },
    ],
    update: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'capacity', label: 'Capacity', type: 'number', min: 1 },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-allocations': {
    title: 'Faculty allocations',
    path: 'allocations',
    create: [
      { key: 'course_id', label: 'Course', type: 'uuid', required: true },
      { key: 'semester_id', label: 'Semester', type: 'uuid', required: true },
      { key: 'section_id', label: 'Section', type: 'uuid', required: true },
      { key: 'faculty_id', label: 'Faculty', type: 'uuid', required: true },
    ],
    update: [
      { key: 'faculty_id', label: 'Faculty', type: 'uuid' },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
  'admin-timetable': {
    title: 'Timetable',
    path: 'timetable',
    create: [
      { key: 'allocation_id', label: 'Allocation', type: 'uuid', required: true },
      { key: 'classroom_id', label: 'Classroom', type: 'uuid', required: true },
      { key: 'weekday', label: 'Weekday (0=Mon)', type: 'number', min: 0, max: 6, required: true },
      { key: 'starts_at', label: 'Starts at', type: 'time', required: true },
      { key: 'ends_at', label: 'Ends at', type: 'time', required: true },
      { key: 'effective_from', label: 'Effective from', type: 'date', required: true },
      { key: 'effective_until', label: 'Effective until', type: 'date' },
    ],
    update: [
      { key: 'allocation_id', label: 'Allocation', type: 'uuid' },
      { key: 'classroom_id', label: 'Classroom', type: 'uuid' },
      { key: 'weekday', label: 'Weekday', type: 'number', min: 0, max: 6 },
      { key: 'starts_at', label: 'Starts at', type: 'time' },
      { key: 'ends_at', label: 'Ends at', type: 'time' },
      { key: 'effective_from', label: 'Effective from', type: 'date' },
      { key: 'effective_until', label: 'Effective until', type: 'date' },
      { key: 'is_active', label: 'Active', type: 'boolean' },
    ],
  },
};

const inputClass =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-primary';

type DeptItem = { id: string; code: string; name: string };
type YearItem = { id: string; name: string };
type SemItem = { id: string; number: number; academic_year_id: string };
type SecItem = { id: string; name: string; department_id: string };
type CourseItem = { id: string; code: string; name: string; department_id: string };
type RoomItem = { id: string; code: string; name: string };
type FacultyItem = { id: string; full_name: string; institutional_id: string };
type AllocItem = { id: string; course_id: string; section_id: string; faculty_id: string };

export const AdminResourceManager: React.FC<{ route: string }> = ({ route }) => {
  const config = resources[route] || resources['admin-departments'];
  const { addToast } = useApp();
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Lookup data for friendly foreign-key selectors
  const [departments, setDepartments] = useState<DeptItem[]>([]);
  const [academicYears, setAcademicYears] = useState<YearItem[]>([]);
  const [semesters, setSemesters] = useState<SemItem[]>([]);
  const [sections, setSections] = useState<SecItem[]>([]);
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [classrooms, setClassrooms] = useState<RoomItem[]>([]);
  const [faculty, setFaculty] = useState<FacultyItem[]>([]);
  const [allocations, setAllocations] = useState<AllocItem[]>([]);

  const fields = selected ? config.update : config.create;
  const labelByKey = useMemo(() => new Map(fields.map((field) => [field.key, field.label])), [fields]);

  const loadLookups = async () => {
    void Promise.allSettled([
      api<DeptItem[]>('/api/admin/departments').then(setDepartments).catch(() => {}),
      api<YearItem[]>('/api/admin/academic-years').then(setAcademicYears).catch(() => {}),
      api<SemItem[]>('/api/admin/semesters').then(setSemesters).catch(() => {}),
      api<SecItem[]>('/api/admin/sections').then(setSections).catch(() => {}),
      api<CourseItem[]>('/api/admin/courses').then(setCourses).catch(() => {}),
      api<RoomItem[]>('/api/admin/classrooms').then(setClassrooms).catch(() => {}),
      api<FacultyItem[]>('/api/admin/users?role=FACULTY&limit=500').then(setFaculty).catch(() => {}),
      api<AllocItem[]>('/api/admin/allocations').then(setAllocations).catch(() => {}),
    ]);
  };

  useEffect(() => {
    void loadLookups();
  }, []);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setRows(await api<Record<string, unknown>[]>(`/api/admin/${config.path}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelected(null);
    setValues({});
    void load();
  }, [route]);

  const choose = (row: Record<string, unknown>) => {
    setSelected(row);
    const next: Record<string, string | boolean> = {};
    config.update.forEach((field) => {
      const value = row[field.key];
      next[field.key] =
        typeof value === 'boolean'
          ? value
          : value == null
          ? ''
          : field.type === 'time'
          ? String(value).slice(0, 5)
          : String(value);
    });
    setValues(next);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    const payload: Record<string, unknown> = {};
    fields.forEach((field) => {
      const raw = values[field.key];
      if (raw === '' || raw === undefined) return;
      payload[field.key] =
        field.type === 'number'
          ? Number(raw)
          : field.type === 'boolean'
          ? raw === true || raw === 'true'
          : raw;
    });

    try {
      if (selected) {
        await api(`/api/admin/${config.path}/${selected.id}`, { method: 'PATCH', body: jsonBody(payload) });
      } else {
        await api(`/api/admin/${config.path}`, { method: 'POST', body: jsonBody(payload) });
      }
      setSelected(null);
      setValues({});
      await load();
      void loadLookups();
      addToast({ type: 'success', message: `${config.title} ${selected ? 'updated' : 'created'}.` });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Save failed.');
    } finally {
      setSaving(false);
    }
  };

  const formatCellValue = (key: string, value: unknown): string => {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'boolean') return value ? 'Active' : 'Inactive';
    const valStr = String(value);

    if (key === 'department_id') {
      const dept = departments.find((d) => d.id === valStr);
      if (dept) return `${dept.code} · ${dept.name}`;
    }
    if (key === 'academic_year_id') {
      const year = academicYears.find((y) => y.id === valStr);
      if (year) return year.name;
    }
    if (key === 'semester_id') {
      const sem = semesters.find((s) => s.id === valStr);
      if (sem) return `Semester ${sem.number}`;
    }
    if (key === 'section_id') {
      const sec = sections.find((s) => s.id === valStr);
      if (sec) return sec.name;
    }
    if (key === 'course_id') {
      const c = courses.find((x) => x.id === valStr);
      if (c) return `${c.code} · ${c.name}`;
    }
    if (key === 'faculty_id') {
      const f = faculty.find((x) => x.id === valStr);
      if (f) return `${f.full_name} (${f.institutional_id})`;
    }
    if (key === 'classroom_id') {
      const r = classrooms.find((x) => x.id === valStr);
      if (r) return `${r.code} · ${r.name}`;
    }
    if (key === 'allocation_id') {
      const a = allocations.find((x) => x.id === valStr);
      if (a) {
        const c = courses.find((x) => x.id === a.course_id);
        const s = sections.find((x) => x.id === a.section_id);
        return `${c ? c.code : a.course_id.slice(0, 6)} · ${s ? s.name : ''}`;
      }
    }
    if (key === 'weekday') {
      const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      return days[Number(value)] ?? String(value);
    }
    return valStr;
  };

  const renderFieldInput = (field: Field) => {
    const val = String(values[field.key] ?? '');

    if (field.type === 'boolean') {
      return (
        <select
          className={inputClass}
          value={String(values[field.key] ?? false)}
          onChange={(event) => setValues({ ...values, [field.key]: event.target.value === 'true' })}
        >
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      );
    }

    if (field.key === 'department_id' && departments.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose department</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} · {d.name}
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'academic_year_id' && academicYears.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose academic year</option>
          {academicYears.map((y) => (
            <option key={y.id} value={y.id}>
              {y.name}
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'semester_id' && semesters.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose semester</option>
          {semesters.map((s) => (
            <option key={s.id} value={s.id}>
              Semester {s.number}
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'section_id' && sections.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose section</option>
          {sections.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'course_id' && courses.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose course</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} · {c.name}
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'faculty_id' && faculty.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose faculty member</option>
          {faculty.map((f) => (
            <option key={f.id} value={f.id}>
              {f.full_name} ({f.institutional_id})
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'classroom_id' && classrooms.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose classroom</option>
          {classrooms.map((r) => (
            <option key={r.id} value={r.id}>
              {r.code} · {r.name}
            </option>
          ))}
        </select>
      );
    }

    if (field.key === 'allocation_id' && allocations.length) {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="">Choose allocation</option>
          {allocations.map((a) => {
            const c = courses.find((x) => x.id === a.course_id);
            const s = sections.find((x) => x.id === a.section_id);
            const f = faculty.find((x) => x.id === a.faculty_id);
            const label = `${c ? c.code : a.course_id.slice(0, 6)} · ${s ? s.name : 'Section'} (${
              f ? f.full_name : 'Faculty'
            })`;
            return (
              <option key={a.id} value={a.id}>
                {label}
              </option>
            );
          })}
        </select>
      );
    }

    if (field.key === 'weekday') {
      return (
        <select
          className={inputClass}
          required={!selected && field.required}
          value={val}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
        >
          <option value="0">Monday</option>
          <option value="1">Tuesday</option>
          <option value="2">Wednesday</option>
          <option value="3">Thursday</option>
          <option value="4">Friday</option>
          <option value="5">Saturday</option>
          <option value="6">Sunday</option>
        </select>
      );
    }

    return (
      <input
        className={inputClass}
        type={field.type === 'uuid' ? 'text' : field.type || 'text'}
        inputMode={field.type === 'uuid' ? 'text' : undefined}
        placeholder={field.type === 'uuid' ? 'UUID' : undefined}
        required={!selected && field.required}
        min={field.min}
        max={field.max}
        value={val}
        onChange={(event) => setValues({ ...values, [field.key]: event.target.value })}
      />
    );
  };

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Administrator · live API</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{config.title}</h1>
        <p className="mt-1 text-sm text-slate-600">
          Manage institutional records and academic configurations stored in the database.
        </p>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      )}

      <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">
            {selected ? `Edit record (${String(selected.id).slice(0, 8)})` : `Create new ${config.title.slice(0, -1)}`}
          </h2>
          {selected && (
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                setValues({});
              }}
              className="text-xs font-medium text-primary-dark hover:underline"
            >
              Cancel edit
            </button>
          )}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map((field) => (
            <label key={field.key} className="space-y-1 text-xs font-medium text-slate-600">
              {field.label}
              {renderFieldInput(field)}
            </label>
          ))}
        </div>

        <button
          disabled={saving}
          className="mt-4 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
        >
          {saving ? 'Saving…' : selected ? 'Save changes' : 'Create record'}
        </button>
      </form>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold">
            {config.title} records ({rows.length})
          </h2>
        </div>
        {loading ? (
          <p className="p-6 text-sm text-slate-500">Loading records…</p>
        ) : rows.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">No records found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-500">
                  <th className="px-5 py-3">ID</th>
                  {fields.slice(0, 4).map((field) => (
                    <th key={field.key} className="px-3 py-3">
                      {labelByKey.get(field.key)}
                    </th>
                  ))}
                  <th className="px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={String(row.id)}>
                    <td className="px-5 py-3 font-mono text-[11px] text-slate-500">
                      {String(row.id).slice(0, 8)}
                    </td>
                    {fields.slice(0, 4).map((field) => (
                      <td key={field.key} className="px-3 py-3 text-slate-700">
                        {formatCellValue(field.key, row[field.key])}
                      </td>
                    ))}
                    <td className="px-5 py-3">
                      <button
                        type="button"
                        onClick={() => choose(row)}
                        className="text-sm font-medium text-primary-dark hover:underline"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
