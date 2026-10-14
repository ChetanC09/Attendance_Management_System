import React, { useEffect, useMemo, useState } from 'react';
import { FileText, Search } from 'lucide-react';
import { api, jsonBody } from '../../services/api';
import { useApp } from '../../context/AppContext';

type Request = {
  id: string;
  student_id: string;
  lecture_id: string | null;
  request_type: string;
  status: string;
  reason: string;
  created_at: string;
  review_reason: string | null;
};

export const FacultyApprovalsView: React.FC = () => {
  const { addToast, setCurrentRoute, setSelectedRequestId } = useApp();
  const [items, setItems] = useState<Request[]>([]);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Request | null>(null);
  const [decisionReason, setDecisionReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await api<Request[]>('/api/faculty/requests'));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const visible = useMemo(
    () =>
      items.filter((item) =>
        `${item.id} ${item.student_id} ${item.request_type} ${item.reason}`
          .toLowerCase()
          .includes(query.trim().toLowerCase()),
      ),
    [items, query],
  );

  const decide = async (action: 'approve' | 'reject') => {
    if (!selected) return;
    if (action === 'reject' && decisionReason.trim().length < 5) {
      setError('A rejection reason of at least 5 characters is required.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api(`/api/faculty/requests/${selected.id}/${action}`, {
        method: 'POST',
        body: jsonBody({ reason: decisionReason.trim() || undefined }),
      });
      setSelected(null);
      setDecisionReason('');
      await load();
      addToast({ type: 'success', message: `Request ${action}d.` });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Decision could not be saved.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <header>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Faculty · live API</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Student attendance requests</h1>
        <p className="mt-1 text-sm text-slate-600">
          Requests are limited by the API to lectures assigned to your account. Approval applies attendance and audit changes transactionally.
        </p>
      </header>

      {error && (
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </p>
      )}

      <label className="relative block max-w-md">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search request, student ID, or reason"
          className="w-full rounded-lg border border-slate-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-primary"
        />
      </label>

      {loading ? (
        <p className="text-sm text-slate-500">Loading requests…</p>
      ) : visible.length ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          {visible.map((item) => (
            <article
              key={item.id}
              className={`rounded-2xl border bg-white p-5 ${
                selected?.id === item.id ? 'border-primary ring-1 ring-primary/20' : 'border-slate-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs text-slate-500">{item.id}</p>
                  <h2 className="mt-1 text-sm font-semibold text-slate-900">
                    {item.request_type} · <span className={item.status === 'APPROVED' ? 'text-emerald-700' : item.status === 'REJECTED' ? 'text-rose-700' : 'text-amber-700'}>{item.status}</span>
                  </h2>
                </div>
                <time className="text-xs text-slate-500">{new Date(item.created_at).toLocaleDateString()}</time>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Student {item.student_id} · Lecture {item.lecture_id || '—'}
              </p>
              <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-700">{item.reason}</p>
              {item.review_reason && (
                <p className="mt-3 rounded-lg bg-slate-50 p-2 text-xs text-slate-600">
                  Review note: {item.review_reason}
                </p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedRequestId(item.id);
                    setCurrentRoute('regularization-detail');
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-primary-dark hover:bg-slate-50"
                >
                  <FileText size={14} />
                  View details & evidence
                </button>
                {item.status === 'PENDING' && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelected(item);
                      setDecisionReason('');
                    }}
                    className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary-dark"
                  >
                    Quick review
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          No assigned requests found.
        </div>
      )}

      {selected && (
        <section className="rounded-2xl border border-primary/30 bg-white p-5">
          <h2 className="text-sm font-semibold">Review selected request</h2>
          <p className="mt-2 text-sm text-slate-600">{selected.reason}</p>
          <label className="mt-4 block text-sm font-medium text-slate-700">
            Decision note
            <textarea
              value={decisionReason}
              onChange={(event) => setDecisionReason(event.target.value)}
              maxLength={2000}
              rows={3}
              className="mt-1.5 block w-full rounded-lg border border-slate-200 p-3 text-sm"
              placeholder="Required when rejecting (minimum 5 characters)"
            />
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              disabled={busy}
              onClick={() => void decide('approve')}
              className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Approve
            </button>
            <button
              disabled={busy}
              onClick={() => void decide('reject')}
              className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-800 disabled:opacity-50"
            >
              Reject
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedRequestId(selected.id);
                setCurrentRoute('regularization-detail');
              }}
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-700"
            >
              Open full details
            </button>
            <button
              onClick={() => setSelected(null)}
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm"
            >
              Cancel
            </button>
          </div>
        </section>
      )}
    </div>
  );
};
