import React, { useMemo, useState } from 'react';
import { Search, Users, X } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import type { EnrolledStudent } from '../../types';

export const StudentAttendanceTrackerView: React.FC = () => {
  const { enrolledStudents } = useApp();
  const [query, setQuery] = useState('');
  const [belowThresholdOnly, setBelowThresholdOnly] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<EnrolledStudent | null>(null);
  const students = useMemo(() => enrolledStudents.filter((student) => {
    const matches = `${student.name} ${student.rollNo} ${student.email}`.toLowerCase().includes(query.trim().toLowerCase());
    return matches && (!belowThresholdOnly || student.aggregatePercentage < 75);
  }).sort((a, b) => a.aggregatePercentage - b.aggregatePercentage), [enrolledStudents, query, belowThresholdOnly]);
  const belowThreshold = enrolledStudents.filter((student) => student.aggregatePercentage < 75).length;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Faculty · sample data</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Class attendance roster</h1>
        <p className="mt-1 text-sm text-slate-600">Review attendance patterns and find students who may need support. Sample values only.</p>
      </div>

      <section className="grid gap-3 sm:grid-cols-2" aria-label="Roster totals">
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4"><span className="grid h-9 w-9 place-items-center rounded-lg bg-primary-container text-primary-dark"><Users size={17} /></span><span><span className="block text-xs text-slate-500">Students in sample</span><strong className="mt-1 block font-mono text-lg text-slate-900">{enrolledStudents.length}</strong></span></div>
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50/60 p-4"><span><span className="block text-xs text-amber-900">Below 75% threshold</span><strong className="mt-1 block font-mono text-lg text-amber-950">{belowThreshold}</strong></span></div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <label className="relative block w-full sm:max-w-sm"><span className="sr-only">Search students</span><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, roll number, or email" className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-primary" /></label>
          <label className="inline-flex items-center gap-2 text-xs text-slate-700"><input type="checkbox" checked={belowThresholdOnly} onChange={(event) => setBelowThresholdOnly(event.target.checked)} className="h-4 w-4 accent-primary" />Below 75% only</label>
        </div>
        {students.length ? <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] border-collapse text-left text-sm">
            <thead><tr className="border-b border-slate-100 text-xs text-slate-500"><th scope="col" className="px-5 py-3 font-medium">Student</th><th scope="col" className="px-4 py-3 font-medium">Section</th><th scope="col" className="px-4 py-3 font-medium">Attendance</th><th scope="col" className="px-4 py-3 font-medium">Courses</th><th scope="col" className="px-4 py-3 font-medium">Open requests</th></tr></thead>
            <tbody className="divide-y divide-slate-100">{students.map((student) => <tr key={student.id} className="hover:bg-slate-50/70">
              <th scope="row" className="px-5 py-3.5 font-medium"><button type="button" onClick={() => setSelectedStudent(student)} className="text-left"><span className="block text-sm font-semibold text-slate-900 hover:text-primary-dark">{student.name}</span><span className="mt-0.5 block font-mono text-[11px] font-normal text-slate-500">{student.rollNo}</span></button></th>
              <td className="px-4 py-3.5 text-slate-700">{student.semester} · {student.division}</td>
              <td className="px-4 py-3.5"><span className={`font-mono font-semibold ${student.aggregatePercentage < 75 ? 'text-amber-800' : 'text-slate-900'}`}>{student.aggregatePercentage}%</span><span className="mt-0.5 block text-[11px] text-slate-500">{student.totalAttended}/{student.totalConducted} sessions</span></td>
              <td className="px-4 py-3.5 font-mono text-slate-700">{student.courses.length}</td>
              <td className="px-4 py-3.5 font-mono text-slate-700">{student.pendingRegularizations}</td>
            </tr>)}</tbody>
          </table>
        </div> : <div className="px-6 py-12 text-center"><p className="text-sm font-medium text-slate-900">No students found</p><p className="mt-1 text-xs text-slate-500">Clear the search or change the filter.</p></div>}
      </section>

      {selectedStudent && <div className="fixed inset-0 z-[70] flex justify-end bg-slate-950/30" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedStudent(null); }}>
        <aside role="dialog" aria-modal="true" aria-labelledby="student-detail-title" className="h-full w-full max-w-lg overflow-y-auto border-l border-slate-200 bg-white p-5 shadow-xl sm:p-7">
          <div className="flex items-start justify-between gap-4"><div><p className="text-xs text-slate-500">Student attendance · sample data</p><h2 id="student-detail-title" className="mt-1 text-xl font-semibold text-slate-900">{selectedStudent.name}</h2><p className="mt-1 font-mono text-xs text-slate-500">{selectedStudent.rollNo}</p></div><button type="button" onClick={() => setSelectedStudent(null)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Close student details"><X size={18} /></button></div>
          <div className="mt-6 rounded-xl border border-slate-200 p-4"><p className="text-xs text-slate-500">Overall attendance</p><p className="mt-1 font-mono text-3xl font-semibold text-slate-900">{selectedStudent.aggregatePercentage}%</p><p className="mt-1 text-xs text-slate-500">{selectedStudent.totalAttended} attended of {selectedStudent.totalConducted} conducted</p></div>
          <h3 className="mt-6 text-sm font-semibold text-slate-900">Course details</h3>
          <ul className="mt-2 divide-y divide-slate-100">{selectedStudent.courses.map((course) => <li key={course.code} className="flex items-center justify-between gap-3 py-3"><span><span className="block text-sm font-medium text-slate-800">{course.name}</span><span className="mt-0.5 block font-mono text-[11px] text-slate-500">{course.code} · {course.attended}/{course.conducted}</span></span><span className={`font-mono text-sm font-semibold ${course.percentage < 75 ? 'text-amber-800' : 'text-slate-900'}`}>{course.percentage}%</span></li>)}</ul>
          <p className="mt-5 rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">This page is read-only in the preview. Use the request review workflow for exceptions; attendance corrections will be connected to the API later.</p>
        </aside>
      </div>}
    </div>
  );
};
