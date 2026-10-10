import React, { useEffect, useMemo, useState } from 'react';
import { Search, ShieldCheck } from 'lucide-react';
import { api } from '../../services/api';

type AuditRecord = { id: string; occurred_at: string; actor_id: string | null; action: string; resource_type: string; resource_id: string | null; before_state: Record<string, unknown> | null; after_state: Record<string, unknown> | null; reason: string | null };

export const SystemLogsSettingsView: React.FC = () => {
  const [auditLogs, setAuditLogs] = useState<AuditRecord[]>([]);
  const [error, setError] = useState('');
  useEffect(() => { api<AuditRecord[]>('/api/admin/audit-logs?limit=500').then(setAuditLogs).catch((reason) => setError(reason instanceof Error ? reason.message : 'Audit logs could not be loaded.')); }, []);
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('all');
  const filteredLogs = useMemo(() => auditLogs.filter((log) => {
    const matchesQuery = `${log.action} ${log.resource_type} ${log.resource_id || ''} ${log.actor_id || ''} ${log.reason || ''}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (severity === 'all' || (severity === 'mutations' && log.action !== 'DELETE') || (severity === 'critical' && log.action === 'DELETE'));
  }), [auditLogs, query, severity]);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <div>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Administrator · live API</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Audit activity</h1>
        <p className="mt-1 text-sm text-slate-600">Review recorded administrative and attendance changes.</p>
      </div>
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <label className="relative block w-full sm:max-w-sm"><span className="sr-only">Search audit activity</span><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search activity or person" className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-primary" /></label>
          <label className="flex items-center gap-2 text-xs text-slate-500">Action<select value={severity} onChange={(event) => setSeverity(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700"><option value="all">All actions</option><option value="mutations">Other actions</option><option value="critical">Deletions</option></select></label>
        </div>
        {filteredLogs.length ? <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead><tr className="border-b border-slate-100 text-xs text-slate-500"><th scope="col" className="px-5 py-3 font-medium">When</th><th scope="col" className="px-4 py-3 font-medium">Activity</th><th scope="col" className="px-4 py-3 font-medium">Actor</th><th scope="col" className="px-4 py-3 font-medium">Severity</th></tr></thead>
            <tbody className="divide-y divide-slate-100">{filteredLogs.map((log) => <tr key={log.id}>
              <td className="whitespace-nowrap px-5 py-3.5 text-xs text-slate-500">{new Date(log.occurred_at).toLocaleString()}</td>
              <td className="px-4 py-3.5"><span className="block text-sm font-medium text-slate-900">{log.action.replaceAll('_', ' ')} · {log.resource_type}</span><span className="mt-0.5 block max-w-2xl text-xs leading-5 text-slate-600">{log.reason || JSON.stringify(log.after_state || {})}</span></td>
              <td className="px-4 py-3.5"><span className="block font-mono text-xs text-slate-800">{log.actor_id || 'System'}</span><span className="mt-0.5 block text-xs text-slate-500">{log.resource_id || '—'}</span></td>
              <td className="px-4 py-3.5"><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium capitalize ${log.action === 'DELETE' ? 'bg-rose-50 text-rose-800' : 'bg-slate-100 text-slate-700'}`}><ShieldCheck size={12} />{log.action === 'DELETE' ? 'critical' : 'recorded'}</span></td>
            </tr>)}</tbody>
          </table>
        </div> : <div className="px-6 py-12 text-center"><p className="text-sm font-medium text-slate-900">No matching activity</p><p className="mt-1 text-xs text-slate-500">Try a different search or severity filter.</p></div>}
      </section>
    </div>
  );
};
