import React, { useEffect, useState } from 'react';
import { api, jsonBody } from '../../services/api';

type Account = {
  id: string;
  institutional_id: string;
  email: string;
  full_name: string;
  phone_number: string | null;
  role: 'ADMIN' | 'FACULTY' | 'STUDENT';
  is_active: boolean;
  department_id?: string | null;
  section_id?: string | null;
  created_at: string;
};

type Department = { id: string; code: string; name: string; is_active: boolean };
type Section = { id: string; name: string; department_id: string; is_active: boolean };

const cls = 'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-primary';

export const AdminUsersView: React.FC<{ role?: 'STUDENT' | 'FACULTY' }> = ({ role }) => {
  const [users, setUsers] = useState<Account[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [values, setValues] = useState({
    institutional_id: '',
    email: '',
    full_name: '',
    password: '',
    role: role || 'STUDENT',
    department_id: '',
    section_id: '',
    phone_number: '',
  });

  const [editing, setEditing] = useState<Account | null>(null);
  const [editName, setEditName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editDept, setEditDept] = useState('');
  const [editSection, setEditSection] = useState('');

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const query = role ? `?role=${role}&limit=500` : '?limit=500';
      const [accountRows, deptRows, sectionRows] = await Promise.all([
        api<Account[]>(`/api/admin/users${query}`),
        api<Department[]>('/api/admin/departments'),
        api<Section[]>('/api/admin/sections'),
      ]);
      setUsers(accountRows);
      setDepartments(deptRows);
      setSections(sectionRows);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [role]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    const payload = {
      ...values,
      role: values.role,
      department_id: values.department_id || null,
      section_id: values.role === 'STUDENT' ? values.section_id || null : null,
      phone_number: values.phone_number || null,
    };
    try {
      await api('/api/admin/users', { method: 'POST', body: jsonBody(payload) });
      setValues({
        ...values,
        institutional_id: '',
        email: '',
        full_name: '',
        password: '',
        phone_number: '',
      });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not create account.');
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (user: Account) => {
    try {
      await api(`/api/admin/users/${user.id}`, {
        method: 'PATCH',
        body: jsonBody({ is_active: !user.is_active }),
      });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update account status.');
    }
  };

  const updateAccount = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!editing) return;
    setBusy(true);
    setError('');
    try {
      await api(`/api/admin/users/${editing.id}`, {
        method: 'PATCH',
        body: jsonBody({
          full_name: editName.trim(),
          phone_number: editPhone || null,
          department_id: editDept || null,
          section_id: editing.role === 'STUDENT' ? editSection || null : null,
        }),
      });
      setEditing(null);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update account profile.');
    } finally {
      setBusy(false);
    }
  };

  const shown = role ? users.filter((user) => user.role === role) : users;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Administrator · live API</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          {role ? `${role === 'STUDENT' ? 'Student' : 'Faculty'} accounts` : 'User directory'}
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Create institutional accounts, assign sections, review current status, and manage access.
        </p>
      </header>

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

      <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Create new account</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['institutional_id', 'Institutional ID (Roll / Emp)', 'text'],
            ['full_name', 'Full name', 'text'],
            ['email', 'Email address', 'email'],
            ['password', 'Temporary password (12+ chars)', 'password'],
            ['phone_number', 'Phone (optional)', 'tel'],
          ].map(([key, label, type]) => (
            <label key={key} className="space-y-1 text-xs font-medium text-slate-600">
              {label}
              <input
                required={key !== 'phone_number'}
                minLength={key === 'password' ? 12 : undefined}
                className={cls}
                type={type}
                value={values[key as keyof typeof values]}
                onChange={(event) => setValues({ ...values, [key]: event.target.value })}
              />
            </label>
          ))}

          {!role && (
            <label className="space-y-1 text-xs font-medium text-slate-600">
              Role
              <select
                className={cls}
                value={values.role}
                onChange={(event) =>
                  setValues({ ...values, role: event.target.value as typeof values.role })
                }
              >
                <option value="STUDENT">Student</option>
                <option value="FACULTY">Faculty</option>
                <option value="ADMIN">Administrator</option>
              </select>
            </label>
          )}

          <label className="space-y-1 text-xs font-medium text-slate-600">
            Department
            <select
              className={cls}
              value={values.department_id}
              onChange={(event) => setValues({ ...values, department_id: event.target.value })}
            >
              <option value="">{values.role === 'STUDENT' ? 'Inherit from section' : 'No department'}</option>
              {departments
                .filter((item) => item.is_active)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} · {item.name}
                  </option>
                ))}
            </select>
          </label>

          {values.role === 'STUDENT' && (
            <label className="space-y-1 text-xs font-medium text-slate-600">
              Section (optional on creation)
              <select
                className={cls}
                value={values.section_id}
                onChange={(event) => setValues({ ...values, section_id: event.target.value })}
              >
                <option value="">Unassigned (Assign later)</option>
                {sections
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      Section {item.name}
                    </option>
                  ))}
              </select>
            </label>
          )}
        </div>
        <button
          disabled={busy}
          className="mt-4 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-60"
        >
          {busy ? 'Creating…' : 'Create Account'}
        </button>
      </form>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Accounts ({shown.length})</h2>
        </div>
        {loading ? (
          <p className="p-6 text-sm text-slate-500">Loading accounts…</p>
        ) : !shown.length ? (
          <p className="p-6 text-sm text-slate-500">No accounts found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-500">
                  <th className="px-5 py-3">Name / ID</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Section / Dept</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {shown.map((user) => {
                  const sec = sections.find((s) => s.id === user.section_id);
                  const dept = departments.find((d) => d.id === user.department_id);
                  return (
                    <tr key={user.id} className="transition hover:bg-slate-50/70">
                      <td className="px-5 py-3">
                        <span className="block font-medium text-slate-900">{user.full_name}</span>
                        <span className="font-mono text-xs text-slate-500">{user.institutional_id}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{user.email}</td>
                      <td className="px-4 py-3">
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {sec ? `Section ${sec.name}` : dept ? dept.code : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
                            user.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="space-x-3 whitespace-nowrap px-5 py-3">
                        <button
                          type="button"
                          onClick={() => {
                            setEditing(user);
                            setEditName(user.full_name);
                            setEditPhone(user.phone_number || '');
                            setEditDept(user.department_id || '');
                            setEditSection(user.section_id || '');
                          }}
                          className="text-xs font-semibold text-primary hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => void toggle(user)}
                          className="text-xs font-semibold text-slate-600 hover:underline"
                        >
                          {user.is_active ? 'Deactivate' : 'Reactivate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Edit User Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
          <form onSubmit={updateAccount} className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="text-base font-semibold text-slate-900">Edit account profile</h2>
            <p className="font-mono text-xs text-slate-500">
              {editing.email} · {editing.institutional_id} ({editing.role})
            </p>

            <label className="block text-xs font-medium text-slate-700">
              Full name
              <input
                required
                minLength={1}
                maxLength={160}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className={`${cls} mt-1`}
              />
            </label>

            <label className="block text-xs font-medium text-slate-700">
              Phone number
              <input
                type="tel"
                placeholder="+12345678901"
                value={editPhone}
                onChange={(e) => setEditPhone(e.target.value)}
                className={`${cls} mt-1`}
              />
            </label>

            <label className="block text-xs font-medium text-slate-700">
              Department
              <select
                value={editDept}
                onChange={(e) => setEditDept(e.target.value)}
                className={`${cls} mt-1`}
              >
                <option value="">No department</option>
                {departments
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.code} · {item.name}
                    </option>
                  ))}
              </select>
            </label>

            {editing.role === 'STUDENT' && (
              <label className="block text-xs font-medium text-slate-700">
                Assigned Section
                <select
                  value={editSection}
                  onChange={(e) => setEditSection(e.target.value)}
                  className={`${cls} mt-1`}
                >
                  <option value="">No section assigned</option>
                  {sections
                    .filter((item) => item.is_active)
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        Section {item.name}
                      </option>
                    ))}
                </select>
              </label>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                disabled={busy}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:opacity-50"
              >
                Save Profile
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
