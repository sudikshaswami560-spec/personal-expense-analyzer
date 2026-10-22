import React from 'react';
import { PlusCircle, Wallet, RefreshCw, Calendar, LogOut, User, LogIn } from 'lucide-react';

export default function Navbar({
  onAddClick,
  onMonthlySummaryClick,
  onRefresh,
  isRefreshing,
  isConnected,
  currentUser,
  onLoginClick,
  onLogoutClick,
}) {
  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
            <Wallet className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 leading-tight">ExpenseFlow</h1>
              <span className="text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                INR
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Private & Multi-Tenant Personal Spending Tracker
            </p>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {/* Status Indicator */}
          <div
            className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isConnected
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}
            title={isConnected ? 'Connected to FastAPI backend' : 'Backend connection error'}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`}
            />
            {isConnected ? 'API Connected' : 'Offline'}
          </div>

          {/* User Account / Auth Actions */}
          {currentUser ? (
            <div className="flex items-center gap-2">
              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs">
                <User className="w-3.5 h-3.5 text-emerald-600" />
                <span className="font-semibold text-slate-700 max-w-[140px] truncate" title={currentUser.email}>
                  {currentUser.full_name || currentUser.email}
                </span>
              </div>
              <button
                onClick={onLogoutClick}
                className="flex items-center gap-1.5 px-3 py-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-lg text-xs font-semibold border border-slate-200 transition-colors"
                title="Log out from this account"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          ) : (
            <button
              onClick={onLoginClick}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-xs font-semibold border border-emerald-200 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          )}

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
            title="Refresh data"
            aria-label="Refresh data"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-600' : ''}`} />
          </button>

          {/* Monthly Summary Button */}
          <button
            onClick={onMonthlySummaryClick}
            disabled={!currentUser}
            className="hidden sm:flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 rounded-lg text-sm font-semibold transition-all duration-150 border border-slate-200 disabled:opacity-50"
            title="Set single total expense for a month"
          >
            <Calendar className="w-4 h-4 text-emerald-600" />
            <span>Monthly Summary</span>
          </button>

          {/* Add Expense Button */}
          <button
            onClick={onAddClick}
            disabled={!currentUser}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold shadow-sm hover:shadow transition-all duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Add Expense</span>
          </button>
        </div>
      </div>
    </header>
  );
}
