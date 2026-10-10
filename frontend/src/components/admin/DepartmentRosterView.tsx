import React, { useMemo, useState } from 'react';
import { Search, Users } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const DepartmentRosterView: React.FC = () => {
  const { departmentStats, enrolledStudents } = useApp();
  const [query, setQuery] = useState('');
  const [department, setDepartment] = useState('all');
  const filteredStudents = useMemo(() => enrolledStudents.filter((student) => {
    const matches = `${student.name} ${student.rollNo} ${student.email}`.toLowerCase().includes(query.trim().toLowerCase());
    return matches && (department === 'all' || student.branch === department);
  }), [enrolledStudents, query, department]);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Administrator · sample data</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Departments and enrollment</h1>
        <p className="mt-1 text-sm text-slate-600">Browse example department summaries and student records.</p>
      </div>
      <div className="rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-xs leading-5 text-amber-950"><strong>Sample data.</strong> Department and student management is read-only in this preview; changes will be connected to the academic administration API later.</div>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Department summaries">
        {departmentStats.map((item) => <article key={item.code} className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-start justify-between gap-3"><span className="font-mono text-xs font-semibold text-primary-dark">{item.code}</span><span className="text-[11px] text-slate-500">Sample</span></div><h2 className="mt-2 text-sm font-semibold text-slate-900">{item.name}</h2><p className="mt-1 text-xs text-slate-500">{item.facultyCount} faculty · {item.enrolledStudents.toLocaleString()} students</p><div className="mt-4 flex items-baseline justify-between border-t border-slate-100 pt-3 text-xs"><span className="text-slate-500">Mean attendance</span><span className="font-mono font-semibold text-slate-900">{item.meanAttendance}%</span></div></article>)}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div className="flex items-center gap-2"><Users size={17} className="text-primary-dark" /><h2 className="text-sm font-semibold text-slate-900">Student directory preview</h2></div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="relative block"><span className="sr-only">Search students</span><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search students" className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-primary sm:w-56" /></label>
            <label className="sr-only" htmlFor="department-filter">Filter by department</label><select id="department-filter" value={department} onChange={(event) => setDepartment(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"><option value="all">All branches</option>{Array.from(new Set(enrolledStudents.map((student) => student.branch))).map((branch) => <option key={branch} value={branch}>{branch}</option>)}</select>
          </div>
        </div>
        {filteredStudents.length ? <div className="overflow-x-auto"><table className="w-full min-w-[560px] border-collapse text-left text-sm"><thead><tr className="border-b border-slate-100 text-xs text-slate-500"><th scope="col" className="px-5 py-3 font-medium">Student</th><th scope="col" className="px-4 py-3 font-medium">Branch</th><th scope="col" className="px-4 py-3 font-medium">Term</th><th scope="col" className="px-4 py-3 font-medium">Attendance</th></tr></thead><tbody className="divide-y divide-slate-100">{filteredStudents.map((student) => <tr key={student.id}><th scope="row" className="px-5 py-3.5 font-medium"><span className="block text-slate-900">{student.name}</span><span className="mt-0.5 block font-mono text-[11px] font-normal text-slate-500">{student.rollNo}</span></th><td className="px-4 py-3.5 text-slate-700">{student.branch}</td><td className="px-4 py-3.5 text-slate-700">{student.semester} · {student.division}</td><td className={`px-4 py-3.5 font-mono font-semibold ${student.aggregatePercentage < 75 ? 'text-amber-800' : 'text-slate-900'}`}>{student.aggregatePercentage}%</td></tr>)}</tbody></table></div> : <p className="px-6 py-10 text-center text-sm text-slate-500">No students match the current filters.</p>}
      </section>
    </div>
  );
};

