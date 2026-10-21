import React, { useState, useRef, useEffect } from 'react';
import {
  Search,
  RotateCcw,
  Calendar,
  Tag,
  CreditCard,
  Download,
  Scale,
  ChevronDown,
  FileSpreadsheet,
  FileText,
  CalendarRange,
} from 'lucide-react';
import { api } from '../api/expenses';

export default function FilterBar({
  filters,
  onFilterChange,
  onResetFilters,
  categories = [],
  paymentMethods = [],
  recordedMonths = [],
  isComparing = false,
  onToggleComparing,
}) {
  const [exportOpen, setExportOpen] = useState(false);
  const exportMenuRef = useRef(null);

  // Close export dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) {
        setExportOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Determine current date mode: 'month', 'quarter', 'year', 'custom', or 'all'
  const dateMode = filters.dateMode || 'month';

  // Available years extracted from recordedMonths or fallback to current year
  const availableYears = Array.from(
    new Set(
      recordedMonths
        .map((m) => m.split('-')[0])
        .concat([new Date().getFullYear().toString()])
    )
  ).sort((a, b) => b.localeCompare(a));

  const hasActiveFilters =
    filters.month !== 'all' ||
    Boolean(filters.start_date) ||
    Boolean(filters.end_date) ||
    filters.category !== 'all' ||
    filters.payment_method !== 'all' ||
    filters.search !== '';

  const formatMonthLabel = (yyyyMm) => {
    try {
      const [year, month] = yyyyMm.split('-');
      const date = new Date(parseInt(year, 10), parseInt(month, 10) - 1, 1);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } catch {
      return yyyyMm;
    }
  };

  const handleDateModeChange = (newMode) => {
    if (newMode === 'all') {
      onFilterChange('dateMode', 'all');
      onFilterChange('month', 'all');
      onFilterChange('start_date', '');
      onFilterChange('end_date', '');
    } else if (newMode === 'month') {
      onFilterChange('dateMode', 'month');
      onFilterChange('start_date', '');
      onFilterChange('end_date', '');
      if (recordedMonths.length > 0 && filters.month === 'all') {
        onFilterChange('month', recordedMonths[0]);
      }
    } else if (newMode === 'quarter') {
      const yr = availableYears[0] || new Date().getFullYear().toString();
      onFilterChange('dateMode', 'quarter');
      onFilterChange('month', 'all');
      onFilterChange('quarterYear', yr);
      onFilterChange('selectedQuarter', 'Q1');
      onFilterChange('start_date', `${yr}-01-01`);
      onFilterChange('end_date', `${yr}-03-31`);
    } else if (newMode === 'year') {
      const yr = availableYears[0] || new Date().getFullYear().toString();
      onFilterChange('dateMode', 'year');
      onFilterChange('month', 'all');
      onFilterChange('selectedYear', yr);
      onFilterChange('start_date', `${yr}-01-01`);
      onFilterChange('end_date', `${yr}-12-31`);
    } else if (newMode === 'custom') {
      onFilterChange('dateMode', 'custom');
      onFilterChange('month', 'all');
    }
  };

  const handleQuarterChange = (q, yr) => {
    const quarters = {
      Q1: [`${yr}-01-01`, `${yr}-03-31`],
      Q2: [`${yr}-04-01`, `${yr}-06-30`],
      Q3: [`${yr}-07-01`, `${yr}-09-30`],
      Q4: [`${yr}-10-01`, `${yr}-12-31`],
    };
    const [start, end] = quarters[q] || quarters.Q1;
    onFilterChange('selectedQuarter', q);
    onFilterChange('quarterYear', yr);
    onFilterChange('start_date', start);
    onFilterChange('end_date', end);
  };

  const handleYearChange = (yr) => {
    onFilterChange('selectedYear', yr);
    onFilterChange('start_date', `${yr}-01-01`);
    onFilterChange('end_date', `${yr}-12-31`);
  };

  // Build export query params
  const getExportParams = () => ({
    month: filters.month !== 'all' ? filters.month : undefined,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined,
    category: filters.category !== 'all' ? filters.category : undefined,
    payment_method: filters.payment_method !== 'all' ? filters.payment_method : undefined,
    search: filters.search || undefined,
  });

  const handleDownload = (type, format) => {
    const params = getExportParams();
    let url = '';
    if (type === 'expenses') {
      url = api.getExportExpensesUrl(params, format);
    } else {
      url = api.getExportSummaryUrl(params, format);
    }
    window.open(url, '_blank');
    setExportOpen(false);
  };

  return (
    <div className="bg-white rounded-2xl p-4 sm:p-5 shadow-sm border border-slate-200/80 space-y-4">
      {/* Upper Bar: Search & Date Range Mode Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Search Bar */}
        <div className="relative flex-1 min-w-[260px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search expenses by description..."
            value={filters.search}
            onChange={(e) => onFilterChange('search', e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all text-slate-800 placeholder-slate-400"
          />
        </div>

        {/* Date Filter Mode Selector */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl text-xs font-semibold overflow-x-auto">
          {[
            { id: 'month', label: 'Month' },
            { id: 'quarter', label: 'Quarter' },
            { id: 'year', label: 'Year' },
            { id: 'custom', label: 'Custom Range' },
            { id: 'all', label: 'All Time' },
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => handleDateModeChange(mode.id)}
              className={`px-3 py-1.5 rounded-lg transition-all shrink-0 ${
                dateMode === mode.id
                  ? 'bg-white text-emerald-700 shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      {/* Dynamic Date Controls based on Selected Mode */}
      <div className="pt-2 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-center">
        {/* Date Control Section */}
        <div className="sm:col-span-2 flex flex-wrap items-center gap-2.5">
          {dateMode === 'month' && (
            <div className="relative flex-1 min-w-[180px]">
              <Calendar className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                value={filters.month}
                onChange={(e) => onFilterChange('month', e.target.value)}
                className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-700 font-medium cursor-pointer"
              >
                <option value="all">All Recorded Months</option>
                {recordedMonths.map((m) => (
                  <option key={m} value={m}>
                    {formatMonthLabel(m)}
                  </option>
                ))}
              </select>
            </div>
          )}

          {dateMode === 'quarter' && (
            <div className="flex items-center gap-2 flex-1">
              <select
                value={filters.selectedQuarter || 'Q1'}
                onChange={(e) =>
                  handleQuarterChange(e.target.value, filters.quarterYear || availableYears[0])
                }
                className="pl-3 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-700 font-medium cursor-pointer"
              >
                <option value="Q1">Q1 (Jan - Mar)</option>
                <option value="Q2">Q2 (Apr - Jun)</option>
                <option value="Q3">Q3 (Jul - Sep)</option>
                <option value="Q4">Q4 (Oct - Dec)</option>
              </select>

              <select
                value={filters.quarterYear || availableYears[0]}
                onChange={(e) =>
                  handleQuarterChange(filters.selectedQuarter || 'Q1', e.target.value)
                }
                className="pl-3 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-700 font-medium cursor-pointer"
              >
                {availableYears.map((yr) => (
                  <option key={yr} value={yr}>
                    {yr}
                  </option>
                ))}
              </select>
            </div>
          )}

          {dateMode === 'year' && (
            <div className="relative flex-1 min-w-[160px]">
              <Calendar className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                value={filters.selectedYear || availableYears[0]}
                onChange={(e) => handleYearChange(e.target.value)}
                className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-700 font-medium cursor-pointer"
              >
                {availableYears.map((yr) => (
                  <option key={yr} value={yr}>
                    Full Year {yr}
                  </option>
                ))}
              </select>
            </div>
          )}

          {dateMode === 'custom' && (
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                <span className="text-[11px] font-semibold text-slate-500">From:</span>
                <input
                  type="date"
                  value={filters.start_date || ''}
                  onChange={(e) => onFilterChange('start_date', e.target.value)}
                  className="bg-transparent text-xs text-slate-800 font-medium focus:outline-none"
                />
              </div>
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                <span className="text-[11px] font-semibold text-slate-500">To:</span>
                <input
                  type="date"
                  value={filters.end_date || ''}
                  onChange={(e) => onFilterChange('end_date', e.target.value)}
                  className="bg-transparent text-xs text-slate-800 font-medium focus:outline-none"
                />
              </div>
            </div>
          )}

          {dateMode === 'all' && (
            <span className="text-xs text-slate-500 italic py-2">
              Showing expenses across all recorded dates.
            </span>
          )}
        </div>

        {/* Category Filter */}
        <div className="relative">
          <Tag className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <select
            value={filters.category}
            onChange={(e) => onFilterChange('category', e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-700 font-medium cursor-pointer"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        {/* Payment Method Filter */}
        <div className="relative">
          <CreditCard className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <select
            value={filters.payment_method}
            onChange={(e) => onFilterChange('payment_method', e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-700 font-medium cursor-pointer"
          >
            <option value="all">All Payment Methods</option>
            {paymentMethods.map((pm) => (
              <option key={pm} value={pm}>
                {pm}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Toolbar: Compare Periods, Export Data, Reset Filters */}
      <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Period Comparison Toggle Button */}
          <button
            type="button"
            onClick={onToggleComparing}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
              isComparing
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700 shadow-xs'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>{isComparing ? 'Hide Comparison' : 'Compare Periods'}</span>
          </button>

          {/* Export Dropdown */}
          <div className="relative" ref={exportMenuRef}>
            <button
              type="button"
              onClick={() => setExportOpen((prev) => !prev)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-all shadow-xs"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Export</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {exportOpen && (
              <div className="absolute left-0 mt-1.5 w-60 bg-white rounded-xl shadow-xl border border-slate-100 py-1.5 z-30 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3 py-1.5 text-[10px] uppercase font-bold tracking-wider text-slate-400 border-b border-slate-100">
                  Export Expenses
                </div>
                <button
                  type="button"
                  onClick={() => handleDownload('expenses', 'csv')}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 flex items-center gap-2.5 transition-colors"
                >
                  <FileText className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="font-semibold block">Expenses as CSV</span>
                    <span className="text-[10px] text-slate-400">Includes UTF-8 BOM for ₹ Rupee support</span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('expenses', 'excel')}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 flex items-center gap-2.5 transition-colors"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="font-semibold block">Expenses as Excel (.xlsx)</span>
                    <span className="text-[10px] text-slate-400">Styled workbook with column widths</span>
                  </div>
                </button>

                <div className="px-3 py-1.5 text-[10px] uppercase font-bold tracking-wider text-slate-400 border-b border-t border-slate-100 mt-1">
                  Export Financial Summary
                </div>
                <button
                  type="button"
                  onClick={() => handleDownload('summary', 'csv')}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 flex items-center gap-2.5 transition-colors"
                >
                  <FileText className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="font-semibold block">Summary as CSV</span>
                    <span className="text-[10px] text-slate-400">KPI metrics & category breakdown</span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('summary', 'excel')}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 flex items-center gap-2.5 transition-colors"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="font-semibold block">Summary as Excel (.xlsx)</span>
                    <span className="text-[10px] text-slate-400">Formatted tables & metrics</span>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Reset Filter Button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 rounded-xl transition-colors"
            title="Clear all active filters"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Filters</span>
          </button>
        )}
      </div>
    </div>
  );
}
