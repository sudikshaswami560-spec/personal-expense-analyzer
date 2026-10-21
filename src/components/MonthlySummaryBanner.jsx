import React from 'react';
import { CalendarCheck, Edit3, Trash2, ShieldCheck } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

export default function MonthlySummaryBanner({
  monthlySummary,
  monthName,
  onEdit,
  onRemove,
}) {
  if (!monthlySummary) return null;

  const { total_amount, itemized_total = 0, itemized_count = 0, note } = monthlySummary;

  return (
    <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 border border-emerald-200/90 rounded-2xl p-4 sm:p-5 shadow-sm text-slate-800 animate-in fade-in duration-200">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-600 text-white shadow-sm shrink-0 mt-0.5">
            <CalendarCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-bold text-slate-900">
                Monthly Summary Active for {monthName}
              </h4>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                <ShieldCheck className="w-3 h-3 text-emerald-600" />
                Anti Double-Counting Active
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Official month total is set to <strong className="text-emerald-800 font-bold">{formatCurrency(total_amount)}</strong>.
              {itemized_count > 0 ? (
                <span>
                  {' '}Preserved {itemized_count} individual expense records totaling {formatCurrency(itemized_total)}.
                </span>
              ) : (
                <span> No individual transactions entered.</span>
              )}
              {note && <span className="italic text-slate-500"> ({note})</span>}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
          <button
            onClick={onEdit}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-white hover:bg-emerald-100/50 rounded-xl border border-emerald-200 shadow-2xs transition-colors"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit Summary</span>
          </button>
          <button
            onClick={onRemove}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-600 bg-white hover:bg-rose-50 rounded-xl border border-rose-200 shadow-2xs transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Remove</span>
          </button>
        </div>
      </div>
    </div>
  );
}
