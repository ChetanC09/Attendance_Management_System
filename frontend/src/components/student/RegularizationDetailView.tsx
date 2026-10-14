import React, { useEffect, useState } from 'react';
import { ArrowLeft, Download, Upload } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { api, apiBlob } from '../../services/api';
type Request = { id: string; student_id: string; lecture_id: string | null; request_type: string; status: string; reason: string; reviewed_by: string | null; review_reason: string | null; reviewed_at: string | null; created_at: string };
type Document = { id: string; original_filename: string; content_type: string; size_bytes: number };
export const RegularizationDetailView: React.FC = () => {
  const { selectedRequestId, currentRole, setCurrentRoute } = useApp(); const [item, setItem] = useState<Request|null>(null); const [documents, setDocuments] = useState<Document[]>([]); const [file, setFile] = useState<File|null>(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [downloading, setDownloading] = useState<string|null>(null);
  const base = currentRole === 'faculty' ? '/api/faculty/requests' : '/api/student/requests';
  useEffect(() => { if (!selectedRequestId) return; api<Request>(`${base}/${selectedRequestId}`).then(setItem).catch((e) => setError(e.message)); api<Document[]>(`${base}/${selectedRequestId}/documents`).then(setDocuments).catch(() => setDocuments([])); }, [selectedRequestId, base]);
  const back = currentRole === 'faculty' ? 'faculty-approvals' : 'leave-medical-slips';
  const upload = async (event: React.FormEvent) => { event.preventDefault(); if (!file || !item) return; setBusy(true); setError(''); const form = new FormData(); form.append('file', file); try { await api(`/api/student/requests/${item.id}/documents`, { method:'POST', body:form }); setDocuments(await api<Document[]>(`/api/student/requests/${item.id}/documents`)); setFile(null); } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed.'); } finally { setBusy(false); } };
  const download = async (document: Document) => {
    setDownloading(document.id); setError('');
    try {
      const path = currentRole === 'faculty'
        ? `/api/faculty/requests/documents/${document.id}`
        : `/api/student/requests/documents/${document.id}`;
      const blob = await apiBlob(path);
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url; link.download = document.original_filename; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Document could not be downloaded.');
    } finally { setDownloading(null); }
  };
  if (!selectedRequestId) return <div className="p-8 text-center text-sm">Choose a request first.</div>;
  return <div className="mx-auto w-full max-w-4xl space-y-5"><button onClick={() => setCurrentRoute(back)} className="inline-flex items-center gap-2 text-sm font-medium text-slate-600"><ArrowLeft size={16}/>Back to requests</button>{error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}{!item ? <p className="text-sm text-slate-500">Loading request…</p> : <><header><p className="text-xs font-medium uppercase tracking-wide text-primary-dark">{currentRole} · live API</p><h1 className="mt-1 text-2xl font-semibold text-slate-900">Request details</h1></header><section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5"><dl className="grid gap-4 sm:grid-cols-2"><div><dt className="text-xs text-slate-500">Request ID</dt><dd className="mt-1 break-all font-mono text-sm">{item.id}</dd></div><div><dt className="text-xs text-slate-500">Status</dt><dd className="mt-1 text-sm font-semibold">{item.status}</dd></div><div><dt className="text-xs text-slate-500">Type</dt><dd className="mt-1 text-sm">{item.request_type}</dd></div><div><dt className="text-xs text-slate-500">Submitted</dt><dd className="mt-1 text-sm">{new Date(item.created_at).toLocaleString()}</dd></div><div className="sm:col-span-2"><dt className="text-xs text-slate-500">Reason</dt><dd className="mt-1 whitespace-pre-wrap text-sm leading-6">{item.reason}</dd></div>{item.review_reason && <div className="sm:col-span-2"><dt className="text-xs text-slate-500">Review note</dt><dd className="mt-1 text-sm">{item.review_reason}</dd></div>}</dl></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-sm font-semibold">Supporting documents</h2>{documents.length ? <ul className="mt-3 divide-y">{documents.map((doc) => <li key={doc.id} className="flex flex-wrap items-center justify-between gap-3 py-2 text-sm text-slate-700"><span className="break-all">{doc.original_filename} · {(doc.size_bytes/1024).toFixed(1)} KB</span><button type="button" disabled={downloading !== null} onClick={() => void download(doc)} className="inline-flex shrink-0 items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-semibold text-primary-dark disabled:opacity-50"><Download size={14}/>{downloading === doc.id ? 'Downloading…' : 'Download'}</button></li>)}</ul> : <p className="mt-2 text-sm text-slate-500">No documents attached.</p>}{currentRole === 'student' && item.status === 'PENDING' && <form onSubmit={upload} className="mt-4 flex flex-wrap items-end gap-3"><label className="text-xs font-medium text-slate-600">Add PDF, PNG, or JPEG<input required type="file" accept="application/pdf,image/png,image/jpeg" onChange={(event) => setFile(event.target.files?.[0] || null)} className="mt-1 block text-sm"/></label><button disabled={busy || !file} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"><Upload size={14}/>{busy?'Uploading…':'Upload'}</button></form>}</section></>}</div>;
};
