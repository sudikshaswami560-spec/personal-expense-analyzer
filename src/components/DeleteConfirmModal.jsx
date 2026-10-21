import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

export default function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  expense = null,
  isDeleting = false,
}) {
  if (!isOpen || !expense) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-100 p-6 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-rose-100 text-rose-600 shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-slate-900">Delete Expense</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Are you sure you want to permanently delete this expense? This action cannot be
              undone.
            </p>

            <div className="mt-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <div className="text-sm font-semibold text-slate-800 truncate">
                {expense.description}
              </div>
              <div className="text-xs text-slate-500 mt-0.5 flex items-center justify-between">
                <span>{expense.category}</span>
                <span className="font-bold text-slate-900">
                  {formatCurrency(expense.amount)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
          >
            {isDeleting && (
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            <span>Delete</span>
          </button>
        </div>
      </div>
    </div>
  );
}
