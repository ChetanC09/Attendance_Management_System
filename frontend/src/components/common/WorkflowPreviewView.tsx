import React from 'react';
import { ArrowRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface WorkflowPreviewViewProps {
  title: string;
  description: string;
  areas?: Array<{ label: string; route: string; detail: string }>;
}

export const WorkflowPreviewView: React.FC<WorkflowPreviewViewProps> = ({ title, description, areas = [] }) => {
  const { setCurrentRoute } = useApp();
  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header><p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary-dark">Administrator · live records</p><h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1><p className="mt-1 text-sm text-slate-600">{description}</p></header>
      <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-700">Choose a directory below. Each directory loads and saves records through the authenticated AMS API.</p>
      {areas.length > 0 && <section aria-label="Academic structure areas" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{areas.map((area) => <button type="button" key={area.route} onClick={() => setCurrentRoute(area.route)} className="flex items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 text-left hover:border-primary-light"><span><span className="block text-sm font-semibold text-slate-900">{area.label}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{area.detail}</span></span><ArrowRight size={16} className="mt-0.5 shrink-0 text-primary-dark"/></button>)}</section>}
      {areas.length === 0 && <section className="rounded-2xl border border-slate-200 bg-white p-6"><h2 className="text-sm font-semibold text-slate-900">Directories available</h2><p className="mt-2 text-sm text-slate-600">Use the administrator navigation to open a record directory.</p></section>}
    </div>
  );
};
