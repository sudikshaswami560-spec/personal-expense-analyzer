import React from 'react';
import { Edit2, Trash2, ArrowUpDown, Calendar, IndianRupee, Tag, CreditCard, SearchX } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

const CATEGORY_BADGES = {
  'Food & Dining': 'bg-orange-50 text-orange-700 border-orange-200',
  Groceries: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Transportation: 'bg-blue-50 text-blue-700 border-blue-200',
  'Housing & Utilities': 'bg-amber-50 text-amber-700 border-amber-200',
  Shopping: 'bg-purple-50 text-purple-700 border-purple-200',
  Entertainment: 'bg-pink-50 text-pink-700 border-pink-200',
  Healthcare: 'bg-red-50 text-red-700 border-red-200',
  Education: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'Personal Care': 'bg-teal-50 text-teal-700 border-teal-200',
  Other: 'bg-slate-100 text-slate-700 border-slate-200',
};

export default function ExpenseTable({
  expenses,
  loading,
  sortBy,
  sortOrder,
  onSort,
  onEdit,
  onDelete,
  onAddNew,
  hasFilters,
  selectedIds = [],
  onToggleSelect,
  onSelectAll,
  onBulkDelete,
}) {
  const allVisibleSelected = expenses.length > 0 && expenses.every((e) => selectedIds.includes(e.id));
  const someVisibleSelected = expenses.some((e) => selectedIds.includes(e.id));
  const selectedCount = selectedIds.length;
  const selectedTotal = expenses
    .filter((e) => selectedIds.includes(e.id))
    .reduce((sum, e) => sum + e.amount, 0);

  const formatDate = (dateStr) => {
    try {
      const [year, month, day] = dateStr.split('-');
      const d = new Date(parseInt(year, 10), parseInt(month, 10) - 1, parseInt(day, 10));
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900 text-base">Expense History</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {expenses.length} {expenses.length === 1 ? 'transaction' : 'transactions'} found
          </p>
        </div>

        {/* Quick Sorting Toggles */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium">Sort by:</span>
          <button
            onClick={() => onSort('date')}
            className={`px-2.5 py-1.5 rounded-lg border font-medium flex items-center gap-1 transition-colors ${
              sortBy === 'date'
                ? 'bg-slate-100 border-slate-300 text-slate-900 font-semibold'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <span>Date</span>
            <ArrowUpDown className="w-3 h-3 text-slate-400" />
            {sortBy === 'date' && (
              <span className="text-[10px] text-slate-500">
                ({sortOrder === 'desc' ? 'Newest' : 'Oldest'})
              </span>
            )}
          </button>
          <button
            onClick={() => onSort('amount')}
            className={`px-2.5 py-1.5 rounded-lg border font-medium flex items-center gap-1 transition-colors ${
              sortBy === 'amount'
                ? 'bg-slate-100 border-slate-300 text-slate-900 font-semibold'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <span>Amount</span>
            <ArrowUpDown className="w-3 h-3 text-slate-400" />
            {sortBy === 'amount' && (
              <span className="text-[10px] text-slate-500">
                ({sortOrder === 'desc' ? 'High' : 'Low'})
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Floating / Sticky Bulk Action Bar */}
      {selectedCount > 0 && (
        <div className="bg-emerald-50 border-b border-emerald-200 px-5 py-3 flex flex-wrap items-center justify-between gap-3 animate-in fade-in duration-150">
          <div className="flex items-center gap-2 text-xs text-emerald-900">
            <span className="font-bold bg-emerald-600 text-white px-2 py-0.5 rounded-full text-[11px]">
              {selectedCount}
            </span>
            <span>
              selected • Total: <strong className="font-bold">{formatCurrency(selectedTotal)}</strong>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onSelectAll(false)}
              className="px-3 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            >
              Deselect All
            </button>
            <button
              onClick={onBulkDelete}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-2xs transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete Selected ({selectedCount})</span>
            </button>
          </div>
        </div>
      )}

      {/* Table Content */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-medium text-slate-500">Loading expenses...</p>
        </div>
      ) : expenses.length === 0 ? (
        /* Empty States */
        <div className="py-16 px-4 flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
            <SearchX className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-semibold text-slate-800">No expenses found</h4>
          <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">
            {hasFilters
              ? 'No transactions matched your active filters. Try adjusting search terms or resetting filters.'
              : 'You haven’t recorded any expenses yet. Start tracking your spending now!'}
          </p>
          {!hasFilters && (
            <button
              onClick={onAddNew}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              Add First Expense
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-100 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {/* Checkbox Select All Column */}
                <th className="py-3 px-4 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={allVisibleSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someVisibleSelected && !allVisibleSelected;
                    }}
                    onChange={(e) => onSelectAll(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 cursor-pointer"
                    title="Select all visible expenses"
                    aria-label="Select all visible expenses"
                  />
                </th>
                <th className="py-3 px-5">Date</th>
                <th className="py-3 px-5">Description</th>
                <th className="py-3 px-5">Category</th>
                <th className="py-3 px-5">Payment Method</th>
                <th className="py-3 px-5 text-right">Amount</th>
                <th className="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {expenses.map((expense) => {
                const isSelected = selectedIds.includes(expense.id);
                const badgeStyle =
                  CATEGORY_BADGES[expense.category] || CATEGORY_BADGES.Other;

                return (
                  <tr
                    key={expense.id}
                    className={`transition-colors group ${
                      isSelected ? 'bg-emerald-50/40 hover:bg-emerald-50/60' : 'hover:bg-slate-50/60'
                    }`}
                  >
                    {/* Checkbox */}
                    <td className="py-3.5 px-4 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect(expense.id)}
                        className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 cursor-pointer"
                        aria-label={`Select ${expense.description}`}
                      />
                    </td>
                    {/* Date */}
                    <td className="py-3.5 px-5 text-xs text-slate-600 font-medium whitespace-nowrap">
                      {formatDate(expense.date)}
                    </td>

                    {/* Description */}
                    <td className="py-3.5 px-5 font-medium text-slate-900 max-w-xs truncate">
                      {expense.description}
                    </td>

                    {/* Category Badge */}
                    <td className="py-3.5 px-5 whitespace-nowrap">
                      <span
                        className={`inline-block px-2.5 py-1 text-xs font-medium rounded-full border ${badgeStyle}`}
                      >
                        {expense.category}
                      </span>
                    </td>

                    {/* Payment Method */}
                    <td className="py-3.5 px-5 text-xs text-slate-600 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium">
                        {expense.payment_method}
                      </span>
                    </td>

                    {/* Amount */}
                    <td className="py-3.5 px-5 text-right font-semibold text-slate-900 whitespace-nowrap">
                      {formatCurrency(expense.amount)}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => onEdit(expense)}
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit expense"
                          aria-label={`Edit ${expense.description}`}
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onDelete(expense)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                          title="Delete expense"
                          aria-label={`Delete ${expense.description}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
