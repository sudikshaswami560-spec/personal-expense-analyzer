import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import SummaryCards from './components/SummaryCards';
import PaymentSummaryCards from './components/PaymentSummaryCards';
import ComparisonCard from './components/ComparisonCard';
import ChartSection from './components/ChartSection';
import FilterBar from './components/FilterBar';
import ExpenseTable from './components/ExpenseTable';
import ExpenseModal from './components/ExpenseModal';
import MonthlySummaryModal from './components/MonthlySummaryModal';
import MonthlySummaryBanner from './components/MonthlySummaryBanner';
import DeleteConfirmModal from './components/DeleteConfirmModal';
import BulkDeleteConfirmModal from './components/BulkDeleteConfirmModal';
import Toast from './components/Toast';
import { api } from './api/expenses';
import { AlertCircle } from 'lucide-react';

export default function App() {
  // Filters State
  const [filters, setFilters] = useState({
    month: 'all',
    category: 'all',
    payment_method: 'all',
    search: '',
    start_date: '',
    end_date: '',
    dateMode: 'all',
    selectedQuarter: 'Q1',
    quarterYear: new Date().getFullYear().toString(),
    selectedYear: new Date().getFullYear().toString(),
  });

  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  // Data State
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [metadata, setMetadata] = useState({
    categories: [],
    payment_methods: [],
    recorded_months: [],
  });

  // Bulk Selection State
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkDeleteModalOpen, setBulkDeleteModalOpen] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  // Period Comparison State
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonPreset, setComparisonPreset] = useState('month');
  const [comparisonData, setComparisonData] = useState(null);
  const [loadingComparison, setLoadingComparison] = useState(false);

  // UI State
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const [apiError, setApiError] = useState(null);
  const [toast, setToast] = useState({ message: null, type: 'info' });

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [monthlySummaryModalOpen, setMonthlySummaryModalOpen] = useState(false);
  const [targetSummaryMonth, setTargetSummaryMonth] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({
    isOpen: false,
    expense: null,
    isDeleting: false,
  });

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
  };

  // Load Metadata (categories, payment methods, recorded months)
  const loadMetadata = async () => {
    try {
      const meta = await api.getMetadata();
      setMetadata(meta);
      setIsConnected(true);
    } catch (err) {
      console.error('Failed to load metadata:', err);
    }
  };

  // Load Expenses and Summary
  const loadData = useCallback(async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    setApiError(null);

    try {
      const queryParams = {
        month: filters.month !== 'all' ? filters.month : undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
        category: filters.category !== 'all' ? filters.category : undefined,
        payment_method: filters.payment_method !== 'all' ? filters.payment_method : undefined,
        search: filters.search || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      const summaryParams = {
        month: filters.month !== 'all' ? filters.month : undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
        category: filters.category !== 'all' ? filters.category : undefined,
        payment_method: filters.payment_method !== 'all' ? filters.payment_method : undefined,
      };

      const [expensesData, summaryData] = await Promise.all([
        api.getExpenses(queryParams),
        api.getSummary(summaryParams),
      ]);

      setExpenses(expensesData);
      setSummary(summaryData);
      setIsConnected(true);
    } catch (err) {
      console.error('Error fetching data:', err);
      setIsConnected(false);
      setApiError(err.message || 'Unable to fetch data from the server');
    } finally {
      if (!isBackground) setLoading(false);
      setIsRefreshing(false);
    }
  }, [filters, sortBy, sortOrder]);

  // Load Comparison Data
  const loadComparison = useCallback(async () => {
    if (!isComparing) return;
    setLoadingComparison(true);
    try {
      let current_start, current_end, prev_start, prev_end, current_label, prev_label;

      if (comparisonPreset === 'quarter') {
        const yr = parseInt(filters.quarterYear || new Date().getFullYear(), 10);
        current_start = `${yr}-07-01`;
        current_end = `${yr}-09-30`;
        prev_start = `${yr}-04-01`;
        prev_end = `${yr}-06-30`;
        current_label = `Q3 ${yr}`;
        prev_label = `Q2 ${yr}`;
      } else if (comparisonPreset === 'year') {
        const yr = parseInt(filters.selectedYear || new Date().getFullYear(), 10);
        current_start = `${yr}-01-01`;
        current_end = `${yr}-12-31`;
        prev_start = `${yr - 1}-01-01`;
        prev_end = `${yr - 1}-12-31`;
        current_label = `Year ${yr}`;
        prev_label = `Year ${yr - 1}`;
      } else {
        // Month comparison
        let curM = filters.month !== 'all' ? filters.month : metadata.recorded_months[0] || '2026-10';
        const [y, m] = curM.split('-').map(Number);
        const curDate = new Date(y, m - 1, 1);
        const prevDate = new Date(y, m - 2, 1);

        const curEndDay = new Date(y, m, 0).getDate();
        const prevEndDay = new Date(prevDate.getFullYear(), prevDate.getMonth() + 1, 0).getDate();

        const curMonthPad = String(m).padStart(2, '0');
        const prevMonthPad = String(prevDate.getMonth() + 1).padStart(2, '0');

        current_start = `${y}-${curMonthPad}-01`;
        current_end = `${y}-${curMonthPad}-${String(curEndDay).padStart(2, '0')}`;
        prev_start = `${prevDate.getFullYear()}-${prevMonthPad}-01`;
        prev_end = `${prevDate.getFullYear()}-${prevMonthPad}-${String(prevEndDay).padStart(2, '0')}`;

        current_label = curDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        prev_label = prevDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      }

      const compResult = await api.getComparison({
        current_start,
        current_end,
        prev_start,
        prev_end,
        current_label,
        prev_label,
      });
      setComparisonData(compResult);
    } catch (err) {
      console.error('Error loading comparison:', err);
      showToast(err.message || 'Failed to calculate period comparison', 'error');
    } finally {
      setLoadingComparison(false);
    }
  }, [isComparing, comparisonPreset, filters.month, filters.quarterYear, filters.selectedYear, metadata.recorded_months]);

  // Initial Load
  useEffect(() => {
    loadMetadata();
  }, []);

  // Fetch when filters or sorting change
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Fetch comparison when isComparing or preset changes
  useEffect(() => {
    if (isComparing) {
      loadComparison();
    }
  }, [isComparing, loadComparison]);

  // Handler for Refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([loadMetadata(), loadData(true)]);
    if (isComparing) await loadComparison();
    setIsRefreshing(false);
    showToast('Data refreshed successfully', 'info');
  };

  // Filter change
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters({
      month: 'all',
      category: 'all',
      payment_method: 'all',
      search: '',
      start_date: '',
      end_date: '',
      dateMode: 'all',
      selectedQuarter: 'Q1',
      quarterYear: new Date().getFullYear().toString(),
      selectedYear: new Date().getFullYear().toString(),
    });
    setSelectedIds([]);
  };

  // Sort change
  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  // Bulk Selection Handlers
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = (forceCheck) => {
    const visibleIds = expenses.map((e) => e.id);
    if (forceCheck === false) {
      setSelectedIds((prev) => prev.filter((id) => !visibleIds.includes(id)));
    } else if (forceCheck === true) {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...visibleIds])));
    } else {
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));
      if (allSelected) {
        setSelectedIds((prev) => prev.filter((id) => !visibleIds.includes(id)));
      } else {
        setSelectedIds((prev) => Array.from(new Set([...prev, ...visibleIds])));
      }
    }
  };

  const handleBulkDeleteConfirm = async () => {
    if (selectedIds.length === 0) return;
    setIsBulkDeleting(true);
    try {
      const res = await api.bulkDeleteExpenses(selectedIds);
      showToast(res.message || `Deleted ${res.deleted_count} expenses`, 'info');
      setSelectedIds([]);
      setBulkDeleteModalOpen(false);
      await loadMetadata();
      await loadData(true);
    } catch (err) {
      showToast(err.message || 'Failed to delete selected expenses', 'error');
    } finally {
      setIsBulkDeleting(false);
    }
  };

  // Create or Update Expense
  const handleSaveExpense = async (payload) => {
    if (editingExpense) {
      // Update
      const updated = await api.updateExpense(editingExpense.id, payload);
      showToast(`Updated "${updated.description}" successfully!`, 'success');
    } else {
      // Create
      const created = await api.createExpense(payload);
      showToast(`Added "${created.description}" for ₹${created.amount.toFixed(2)}`, 'success');
    }
    // Refresh list, summary, and metadata
    await loadMetadata();
    await loadData(true);
  };

  // Trigger Edit
  const handleEditClick = (expense) => {
    setEditingExpense(expense);
    setModalOpen(true);
  };

  // Trigger Single Delete Modal
  const handleDeleteClick = (expense) => {
    setDeleteDialog({
      isOpen: true,
      expense,
      isDeleting: false,
    });
  };

  // Confirm Single Delete
  const handleConfirmDelete = async () => {
    const expense = deleteDialog.expense;
    if (!expense) return;

    setDeleteDialog((prev) => ({ ...prev, isDeleting: true }));
    try {
      await api.deleteExpense(expense.id);
      showToast(`Deleted "${expense.description}"`, 'info');
      setDeleteDialog({ isOpen: false, expense: null, isDeleting: false });
      setSelectedIds((prev) => prev.filter((id) => id !== expense.id));
      await loadMetadata();
      await loadData(true);
    } catch (err) {
      showToast(err.message || 'Failed to delete expense', 'error');
      setDeleteDialog((prev) => ({ ...prev, isDeleting: false }));
    }
  };

  // Open Monthly Summary Modal
  const handleOpenMonthlySummary = (month = null) => {
    setTargetSummaryMonth(month || (filters.month !== 'all' ? filters.month : null));
    setMonthlySummaryModalOpen(true);
  };

  // Callback when Monthly Summary is saved or deleted
  const handleMonthlySummarySaved = async (message) => {
    showToast(message, 'success');
    await loadMetadata();
    await loadData(true);
  };

  // Remove Monthly Summary directly from banner
  const handleRemoveMonthlySummary = async () => {
    if (!filters.month || filters.month === 'all') return;
    try {
      await api.deleteMonthlySummary(filters.month);
      showToast('Monthly summary removed. Reverted to itemized total.', 'info');
      await loadMetadata();
      await loadData(true);
    } catch (err) {
      showToast(err.message || 'Failed to remove monthly summary', 'error');
    }
  };

  // Selected Month label
  const selectedMonthLabel =
    filters.month !== 'all'
      ? (() => {
          try {
            const [y, m] = filters.month.split('-');
            const d = new Date(parseInt(y, 10), parseInt(m, 10) - 1, 1);
            return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
          } catch {
            return filters.month;
          }
        })()
      : null;

  const hasActiveFilters =
    filters.month !== 'all' ||
    Boolean(filters.start_date) ||
    Boolean(filters.end_date) ||
    filters.category !== 'all' ||
    filters.payment_method !== 'all' ||
    filters.search !== '';

  const selectedTotal = expenses
    .filter((e) => selectedIds.includes(e.id))
    .reduce((sum, e) => sum + e.amount, 0);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-emerald-500 selection:text-white">
      {/* Toast Notification */}
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: null, type: 'info' })}
      />

      {/* Top Navbar */}
      <Navbar
        onAddClick={() => {
          setEditingExpense(null);
          setModalOpen(true);
        }}
        onMonthlySummaryClick={() => handleOpenMonthlySummary()}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        isConnected={isConnected}
      />

      {/* Main Dashboard Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* API Disconnected Alert */}
        {apiError && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start gap-3 text-rose-800 animate-in fade-in duration-200">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-bold text-rose-900">Backend Connection Error</h4>
              <p className="text-xs text-rose-700 mt-0.5">{apiError}</p>
              <button
                onClick={handleRefresh}
                className="mt-2 text-xs font-semibold underline hover:text-rose-900"
              >
                Click to retry connection
              </button>
            </div>
          </div>
        )}

        {/* Active Monthly Summary Banner */}
        {summary?.has_monthly_summary && summary?.monthly_summary && (
          <MonthlySummaryBanner
            monthlySummary={summary.monthly_summary}
            monthName={selectedMonthLabel || filters.month}
            onEdit={() => handleOpenMonthlySummary(filters.month)}
            onRemove={handleRemoveMonthlySummary}
          />
        )}

        {/* 1. KPI Metric Summary Cards */}
        <SummaryCards
          summary={summary}
          selectedMonthName={selectedMonthLabel}
        />

        {/* 2. Period Comparison Card (when active) */}
        {isComparing && (
          <ComparisonCard
            comparison={comparisonData}
            onClose={() => setIsComparing(false)}
            preset={comparisonPreset}
            onPresetChange={(p) => setComparisonPreset(p)}
            loading={loadingComparison}
          />
        )}

        {/* 3. Payment Method Breakdown Cards */}
        {summary?.payment_methods && (
          <PaymentSummaryCards
            paymentSummaries={summary.payment_methods}
            totalSpending={summary.total_spending}
          />
        )}

        {/* 4. Visual Charts (Category Donut & Monthly Trend Bar) */}
        <ChartSection summary={summary} />

        {/* 5. Filter & Export Bar */}
        <FilterBar
          filters={filters}
          onFilterChange={handleFilterChange}
          onResetFilters={handleResetFilters}
          categories={metadata.categories}
          paymentMethods={metadata.payment_methods}
          recordedMonths={metadata.recorded_months}
          isComparing={isComparing}
          onToggleComparing={() => setIsComparing((prev) => !prev)}
        />

        {/* 6. Expenses Table with Checkboxes & Bulk Action Bar */}
        <ExpenseTable
          expenses={expenses}
          loading={loading}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSort={handleSort}
          onEdit={handleEditClick}
          onDelete={handleDeleteClick}
          onAddNew={() => {
            setEditingExpense(null);
            setModalOpen(true);
          }}
          hasFilters={hasActiveFilters}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
          onSelectAll={handleSelectAll}
          onBulkDelete={() => setBulkDeleteModalOpen(true)}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <p>
            Personal Expense Analyzer • Built with React, Vite, Tailwind CSS, Chart.js &amp; FastAPI
          </p>
          <div className="flex items-center gap-4">
            <span>FastAPI REST API: <code className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-mono">http://localhost:8000</code></span>
          </div>
        </div>
      </footer>

      {/* Add / Edit Expense Modal */}
      <ExpenseModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditingExpense(null);
        }}
        onSubmit={handleSaveExpense}
        initialData={editingExpense}
        categories={metadata.categories}
        paymentMethods={metadata.payment_methods}
      />

      {/* Single Expense Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteDialog.isOpen}
        onClose={() => setDeleteDialog({ isOpen: false, expense: null, isDeleting: false })}
        onConfirm={handleConfirmDelete}
        expense={deleteDialog.expense}
        isDeleting={deleteDialog.isDeleting}
      />

      {/* Bulk Delete Confirmation Modal */}
      <BulkDeleteConfirmModal
        isOpen={bulkDeleteModalOpen}
        onClose={() => setBulkDeleteModalOpen(false)}
        onConfirm={handleBulkDeleteConfirm}
        selectedCount={selectedIds.length}
        selectedTotal={selectedTotal}
        isDeleting={isBulkDeleting}
      />

      {/* Monthly Expense Summary Modal */}
      <MonthlySummaryModal
        isOpen={monthlySummaryModalOpen}
        onClose={() => setMonthlySummaryModalOpen(false)}
        onSaved={handleMonthlySummarySaved}
        initialMonth={targetSummaryMonth}
      />
    </div>
  );
}
