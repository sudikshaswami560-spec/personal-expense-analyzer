import React from 'react';
import { Smartphone, Banknote, CreditCard, Landmark, CircleDollarSign } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

const PAYMENT_CONFIG = {
  UPI: {
    icon: Smartphone,
    label: 'UPI Payments',
    bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    barBg: 'bg-emerald-500',
    badge: 'Popular',
  },
  Cash: {
    icon: Banknote,
    label: 'Cash Spending',
    bg: 'bg-amber-50 text-amber-700 border-amber-200',
    barBg: 'bg-amber-500',
  },
  'Credit Card': {
    icon: CreditCard,
    label: 'Credit Cards',
    bg: 'bg-blue-50 text-blue-700 border-blue-200',
    barBg: 'bg-blue-500',
  },
  'Debit Card': {
    icon: CreditCard,
    label: 'Debit Cards',
    bg: 'bg-purple-50 text-purple-700 border-purple-200',
    barBg: 'bg-purple-500',
  },
  'Bank Transfer': {
    icon: Landmark,
    label: 'Bank Transfer / NetBanking',
    bg: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    barBg: 'bg-indigo-500',
  },
  'UPI / Bank Transfer': {
    icon: Smartphone,
    label: 'UPI / NetBanking',
    bg: 'bg-teal-50 text-teal-700 border-teal-200',
    barBg: 'bg-teal-500',
  },
  Other: {
    icon: CircleDollarSign,
    label: 'Other Methods',
    bg: 'bg-slate-50 text-slate-700 border-slate-200',
    barBg: 'bg-slate-500',
  },
};

export default function PaymentSummaryCards({ paymentSummaries = [], totalSpending = 0 }) {
  if (!paymentSummaries || paymentSummaries.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200/80">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm">Payment Method Breakdown</h3>
          <p className="text-xs text-slate-500">Spending distribution across UPI, cards, cash &amp; banking</p>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
          {paymentSummaries.length} channels
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {paymentSummaries.map((item, idx) => {
          const config = PAYMENT_CONFIG[item.payment_method] || PAYMENT_CONFIG.Other;
          const IconComponent = config.icon;
          const pct = item.percentage || 0;

          return (
            <div
              key={idx}
              className={`p-4 rounded-xl border transition-all duration-150 hover:shadow-xs flex flex-col justify-between ${config.bg}`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <IconComponent className="w-4 h-4" />
                    <span className="text-xs font-bold">{item.payment_method}</span>
                  </div>
                  {config.badge && (
                    <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 bg-emerald-200/80 text-emerald-900 rounded">
                      {config.badge}
                    </span>
                  )}
                </div>

                <div className="text-xl font-bold text-slate-900 mt-1">
                  {formatCurrency(item.total_amount)}
                </div>

                <div className="flex items-center justify-between text-xs text-slate-600 mt-1">
                  <span>{item.count} {item.count === 1 ? 'transaction' : 'transactions'}</span>
                  <span className="font-semibold text-slate-800">{pct}%</span>
                </div>
              </div>

              {/* Mini progress meter */}
              <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden mt-3">
                <div
                  className={`h-full ${config.barBg} rounded-full transition-all duration-300`}
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
