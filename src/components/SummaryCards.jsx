import React from 'react';
import { IndianRupee, Receipt, TrendingUp, Award } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

export default function SummaryCards({ summary, selectedMonthName }) {
  const {
    total_spending = 0,
    total_expenses_count = 0,
    average_expense = 0,
    highest_expense = 0,
    categories = [],
  } = summary || {};

  const topCategory = categories && categories.length > 0 ? categories[0] : null;

  const isMonthlySummary = summary?.has_monthly_summary;

  const cards = [
    {
      title: 'Total Spending',
      subtitle: isMonthlySummary
        ? `Set via Monthly Summary (${selectedMonthName || 'Month'})`
        : selectedMonthName
        ? `In ${selectedMonthName}`
        : 'All recorded time',
      value: formatCurrency(total_spending),
      icon: IndianRupee,
      iconBg: isMonthlySummary
        ? 'bg-emerald-200 text-emerald-800'
        : 'bg-emerald-100 text-emerald-600',
      borderAccent: isMonthlySummary
        ? 'border-l-4 border-l-emerald-600 ring-1 ring-emerald-300'
        : 'border-l-4 border-l-emerald-500',
    },
    {
      title: 'Number of Expenses',
      subtitle: 'Recorded transactions',
      value: total_expenses_count.toLocaleString(),
      icon: Receipt,
      iconBg: 'bg-blue-100 text-blue-600',
      borderAccent: 'border-l-4 border-l-blue-500',
    },
    {
      title: 'Average Expense',
      subtitle: 'Per transaction',
      value: formatCurrency(average_expense),
      icon: TrendingUp,
      iconBg: 'bg-violet-100 text-violet-600',
      borderAccent: 'border-l-4 border-l-violet-500',
    },
    {
      title: 'Top Category',
      subtitle: topCategory ? `${topCategory.percentage}% of total` : 'No category data',
      value: topCategory ? topCategory.category : 'N/A',
      secondaryValue: topCategory ? formatCurrency(topCategory.total_amount) : null,
      icon: Award,
      iconBg: 'bg-amber-100 text-amber-600',
      borderAccent: 'border-l-4 border-l-amber-500',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
      {cards.map((card, idx) => {
        const IconComponent = card.icon;
        return (
          <div
            key={idx}
            className={`bg-white rounded-2xl p-5 shadow-sm border border-slate-200/80 hover:shadow-md transition-all duration-200 flex flex-col justify-between ${card.borderAccent}`}
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {card.title}
                </span>
                <div className="text-2xl font-bold text-slate-900 mt-1 truncate">
                  {card.value}
                </div>
                {card.secondaryValue && (
                  <div className="text-xs font-medium text-slate-500 mt-0.5">
                    {card.secondaryValue}
                  </div>
                )}
              </div>
              <div className={`p-2.5 rounded-xl ${card.iconBg}`}>
                <IconComponent className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500 flex items-center gap-1 font-medium">
              <span>{card.subtitle}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
