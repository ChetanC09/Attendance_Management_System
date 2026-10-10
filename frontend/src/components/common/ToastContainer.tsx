import React from 'react';
import { useApp } from '../../context/AppContext';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { toasts, dismissToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm pointer-events-none">
      {toasts.map((toast) => {
        let borderColor = 'border-emerald-200';
        let IconComponent = CheckCircle2;
        let iconColor = 'text-emerald-600';
        let bgColor = 'bg-white';

        if (toast.type === 'error') {
          borderColor = 'border-rose-200';
          IconComponent = AlertCircle;
          iconColor = 'text-rose-600';
        } else if (toast.type === 'warning') {
          borderColor = 'border-amber-200';
          IconComponent = AlertTriangle;
          iconColor = 'text-amber-600';
        } else if (toast.type === 'info') {
          borderColor = 'border-blue-200';
          IconComponent = Info;
          iconColor = 'text-blue-600';
        }

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto ${bgColor} border ${borderColor} rounded-xl p-3.5 shadow-lg shadow-slate-900/5 flex items-start gap-3 transition-all duration-300 animate-in fade-in slide-in-from-bottom-2`}
          >
            <IconComponent className={`h-5 w-5 ${iconColor} mt-0.5 shrink-0`} />
            <div className="flex-1 min-w-0">
              {toast.title && (
                <div className="font-semibold text-xs text-slate-900 mb-0.5">
                  {toast.title}
                </div>
              )}
              <div className="text-xs text-slate-600 leading-snug">{toast.message}</div>
            </div>
            <button
              onClick={() => dismissToast(toast.id)}
              className="text-slate-400 hover:text-slate-600 p-0.5 rounded transition-colors shrink-0"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
