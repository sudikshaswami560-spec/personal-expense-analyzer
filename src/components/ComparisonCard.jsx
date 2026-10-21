import React from 'react';
import { ArrowUpRight, ArrowDownRight, Scale, X, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

export default function ComparisonCard({
  comparison,
  onClose,
  preset = 'month',
  onPresetChange,
  loading = false,
}) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-indigo-100 ring-1 ring-indigo-500/10 animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl shrink-0">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Period-over-Period Financial Comparison</h3>
            <p className="text-xs text-slate-500">
              {comparison ? (
                <>
                  Comparing <strong className="text-slate-800">{comparison.current_period_label}</strong> with{' '}
                  <strong className="text-slate-800">{comparison.previous_period_label}</strong>
                </>
              ) : (
                'Analyze shifts in spending volume and category distribution'
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          {onPresetChange && (
            <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-xs font-semibold">
              <button
                type="button"
                onClick={() => onPresetChange('month')}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  preset === 'month' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => onPresetChange('quarter')}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  preset === 'quarter' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Quarterly
              </button>
              <button
                type="button"
                onClick={() => onPresetChange('year')}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  preset === 'year' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Yearly
              </button>
            </div>
          )}

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors ml-1"
              title="Close comparison"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
          <span className="text-xs font-medium">Calculating period deltas...</span>
        </div>
      ) : !comparison ? (
        <div className="py-6 text-center text-xs text-slate-500">
          No comparison data available for this range.
        </div>
      ) : (
        <>
          {/* Main 3 Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mb-5">
            {/* Current Period */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] uppercase font-bold tracking-wider text-slate-500 block">
                {comparison.current_period_label}
              </span>
              <div className="text-2xl font-bold text-slate-900 mt-1">
                {formatCurrency(comparison.current_period_spending)}
              </div>
              <span className="text-xs text-slate-500 mt-0.5 block">
                {comparison.current_period_count} transactions
              </span>
            </div>

            {/* Previous Period */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] uppercase font-bold tracking-wider text-slate-500 block">
                {comparison.previous_period_label}
              </span>
              <div className="text-2xl font-bold text-slate-900 mt-1">
                {formatCurrency(comparison.previous_period_spending)}
              </div>
              <span className="text-xs text-slate-500 mt-0.5 block">
                {comparison.previous_period_count} transactions
              </span>
            </div>

            {/* Net Change */}
            <div
              className={`p-4 rounded-xl border flex flex-col justify-between ${
                comparison.difference > 0
                  ? 'bg-rose-50/70 border-rose-200 text-rose-900'
                  : comparison.difference === 0
                  ? 'bg-slate-50 border-slate-200 text-slate-800'
                  : 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] uppercase font-bold tracking-wider">Net Change</span>
                <span
                  className={`inline-flex items-center gap-0.5 text-xs font-bold px-2 py-0.5 rounded-full ${
                    comparison.difference > 0
                      ? 'bg-rose-200 text-rose-800'
                      : comparison.difference === 0
                      ? 'bg-slate-200 text-slate-800'
                      : 'bg-emerald-200 text-emerald-800'
                  }`}
                >
                  {comparison.difference > 0 ? (
                    <>
                      <TrendingUp className="w-3 h-3" /> +{comparison.percentage_change}%
                    </>
                  ) : comparison.difference === 0 ? (
                    '0.0%'
                  ) : (
                    <>
                      <TrendingDown className="w-3 h-3" /> {comparison.percentage_change}%
                    </>
                  )}
                </span>
              </div>

              <div className="text-2xl font-bold mt-1">
                {comparison.difference > 0
                  ? `+${formatCurrency(comparison.difference)}`
                  : formatCurrency(comparison.difference)}
              </div>
              <span className="text-xs opacity-80 mt-0.5 block">
                {comparison.difference > 0
                  ? 'Spending increased'
                  : comparison.difference === 0
                  ? 'Zero variance'
                  : 'Spending reduced'}
              </span>
            </div>
          </div>

          {/* Category Shifts Breakdown */}
          {comparison.category_deltas && comparison.category_deltas.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5">
                Category Spending Shifts
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {comparison.category_deltas.slice(0, 6).map((item, idx) => {
                  const inc = item.delta > 0;
                  return (
                    <div
                      key={idx}
                      className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80 flex items-center justify-between text-xs"
                    >
                      <div className="truncate mr-2">
                        <span className="font-semibold text-slate-800 block truncate">{item.category}</span>
                        <span className="text-[11px] text-slate-500">
                          {formatCurrency(item.current_amount)} vs {formatCurrency(item.previous_amount)}
                        </span>
                      </div>

                      <div className={`text-right shrink-0 font-bold ${inc ? 'text-rose-600' : 'text-emerald-600'}`}>
                        <span>{inc ? `+${formatCurrency(item.delta)}` : formatCurrency(item.delta)}</span>
                        <span className="block text-[10px] font-medium opacity-80">
                          {item.percentage_change > 0 ? `+${item.percentage_change}%` : `${item.percentage_change}%`}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
