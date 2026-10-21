import React, { useState, useEffect } from 'react';
import { X, Calendar, IndianRupee, FileText, AlertTriangle, Info, Trash2 } from 'lucide-react';
import { api } from '../api/expenses';
import { formatCurrency } from '../utils/currency';

export default function MonthlySummaryModal({
  isOpen,
  onClose,
  onSaved,
  initialMonth = null,
}) {
  const currentDate = new Date();
  const defaultYear = initialMonth ? parseInt(initialMonth.split('-')[0], 10) : currentDate.getFullYear();
  const defaultMonth = initialMonth ? parseInt(initialMonth.split('-')[1], 10) : currentDate.getMonth() + 1;

  const [year, setYear] = useState(defaultYear);
  const [monthNumber, setMonthNumber] = useState(defaultMonth);
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [loadingContext, setLoadingContext] = useState(false);
  const [existingSummary, setExistingSummary] = useState(null);
  const [itemizedStats, setItemizedStats] = useState({ total: 0, count: 0 });
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  const selectedMonthString = `${year}-${String(monthNumber).padStart(2, '0')}`;

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  // Fetch month context (itemized expenses + existing summary if any)
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    async function fetchMonthContext() {
      setLoadingContext(true);
      setError(null);
      try {
        const [expenses, summaries] = await Promise.all([
          api.getExpenses({ month: selectedMonthString }),
          api.getMonthlySummaries(),
        ]);

        if (!isMounted) return;

        const itemSum = expenses.reduce((acc, curr) => acc + curr.amount, 0);
        setItemizedStats({
          total: Math.round(itemSum * 100) / 100,
          count: expenses.length,
        });

        const found = summaries.find((s) => s.month === selectedMonthString);
        if (found) {
          setExistingSummary(found);
          setAmount(found.total_amount.toString());
          setNote(found.note || '');
        } else {
          setExistingSummary(null);
          setAmount('');
          setNote('');
        }
      } catch (err) {
        console.error('Error fetching month context:', err);
      } finally {
        if (isMounted) setLoadingContext(false);
      }
    }

    fetchMonthContext();
    return () => {
      isMounted = false;
    };
  }, [isOpen, selectedMonthString]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Please enter a valid total amount greater than ₹0.00');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await api.saveMonthlySummary({
        month: selectedMonthString,
        total_amount: numAmount,
        note: note.trim() || null,
      });
      onSaved(`Monthly summary for ${monthNames[monthNumber - 1]} ${year} set to ${formatCurrency(numAmount)}!`);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save monthly summary');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!existingSummary) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteMonthlySummary(selectedMonthString);
      onSaved(`Monthly summary removed. Reverted to itemized total.`);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to remove monthly summary');
    } finally {
      setDeleting(false);
    }
  };

  const selectedMonthDisplay = `${monthNames[monthNumber - 1]} ${year}`;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-100 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Monthly Expense Summary</h3>
            <p className="text-xs text-slate-500">Record a single lump-sum total for an entire month</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Month & Year Selectors */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Month *
              </label>
              <select
                value={monthNumber}
                onChange={(e) => setMonthNumber(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 cursor-pointer"
              >
                {monthNames.map((name, idx) => (
                  <option key={name} value={idx + 1}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Year *
              </label>
              <select
                value={year}
                onChange={(e) => setYear(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 cursor-pointer"
              >
                {[year - 2, year - 1, year, year + 1].map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Context Notice / Anti Double-Counting Explanation */}
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs space-y-2">
            <div className="flex items-start gap-2 text-slate-700">
              <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-semibold text-slate-900">{selectedMonthDisplay} Status: </span>
                {itemizedStats.count > 0 ? (
                  <span>
                    Has <strong className="text-slate-900">{itemizedStats.count}</strong> individual expense records totaling{' '}
                    <strong className="text-slate-900">{formatCurrency(itemizedStats.total)}</strong>.
                  </span>
                ) : (
                  <span>No individual itemized records found for this month.</span>
                )}
              </div>
            </div>

            {itemizedStats.count > 0 && (
              <div className="flex items-start gap-2 text-amber-800 bg-amber-50/80 p-2.5 rounded-lg border border-amber-200/80">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong>Double-Counting Prevention:</strong> This entered summary will be treated as the official total spending for{' '}
                  {selectedMonthDisplay}. All {itemizedStats.count} individual receipts will remain safely preserved and will not be added twice.
                </div>
              </div>
            )}
          </div>

          {/* Total Amount Input */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
              Overall Total Spending (₹) *
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-sm">
                ₹
              </span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="e.g., 850.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full pl-8 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                autoFocus
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Enter your estimated or bank statement total in Rupees when itemized receipts are not entered.
            </p>
          </div>

          {/* Note Input */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
              Note (Optional)
            </label>
            <div className="relative">
              <FileText className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="e.g., Total estimated from September bank statement"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={255}
                className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 flex items-center justify-between border-t border-slate-100">
            {existingSummary ? (
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting || submitting}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-xl transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{deleting ? 'Removing...' : 'Remove Summary'}</span>
              </button>
            ) : (
              <div />
            )}

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || deleting}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-sm transition-all flex items-center gap-2 active:scale-95 disabled:opacity-50"
              >
                {submitting && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                <span>{existingSummary ? 'Update Summary' : 'Set Monthly Summary'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
