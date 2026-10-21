import React from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { PieChart, TrendingUp, Inbox } from 'lucide-react';
import { formatCurrency } from '../utils/currency';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

const CATEGORY_COLORS = [
  '#10b981', // emerald
  '#3b82f6', // blue
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#6366f1', // indigo
  '#14b8a6', // teal
  '#64748b', // slate
];

export default function ChartSection({ summary }) {
  const { categories = [], monthly_trends = [], total_spending = 0 } = summary || {};

  // 1. Doughnut Chart for Categories
  const categoryLabels = categories.map((c) => c.category);
  const categoryDataValues = categories.map((c) => c.total_amount);
  const categoryColors = categories.map((_, i) => CATEGORY_COLORS[i % CATEGORY_COLORS.length]);

  const doughnutData = {
    labels: categoryLabels,
    datasets: [
      {
        data: categoryDataValues,
        backgroundColor: categoryColors,
        borderColor: '#ffffff',
        borderWidth: 2,
        hoverOffset: 6,
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 12,
          boxHeight: 12,
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 14,
          font: {
            size: 11,
            family: 'Inter, sans-serif',
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.label || '';
            const value = context.parsed || 0;
            const pct = total_spending > 0 ? ((value / total_spending) * 100).toFixed(1) : 0;
            return ` ${label}: ${formatCurrency(value)} (${pct}%)`;
          },
        },
      },
    },
    cutout: '68%',
  };

  // 2. Bar Chart for Monthly Trends
  const trendLabels = monthly_trends.map((t) => t.month_name);
  const trendValues = monthly_trends.map((t) => t.total_amount);
  const barBackgroundColors = monthly_trends.map((t) => (t.is_summary ? '#059669' : '#10b981'));
  const barHoverColors = monthly_trends.map((t) => (t.is_summary ? '#047857' : '#059669'));

  const barData = {
    labels: trendLabels,
    datasets: [
      {
        label: 'Monthly Total',
        data: trendValues,
        backgroundColor: barBackgroundColors,
        hoverBackgroundColor: barHoverColors,
        borderRadius: 8,
        borderSkipped: false,
        maxBarThickness: 42,
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const index = context.dataIndex;
            const trendItem = monthly_trends[index];
            const value = context.parsed.y || 0;
            if (trendItem && trendItem.is_summary) {
              return [
                ` Total Spending: ${formatCurrency(value)} (Monthly Summary)`,
                ` Itemized Records: ${formatCurrency(trendItem.itemized_amount)} (${trendItem.itemized_count} entries)`,
              ];
            }
            return ` Spending: ${formatCurrency(value)}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
            family: 'Inter, sans-serif',
          },
          color: '#64748b',
        },
      },
      y: {
        beginAtZero: true,
        grid: {
          color: '#f1f5f9',
        },
        ticks: {
          font: {
            size: 11,
            family: 'Inter, sans-serif',
          },
          color: '#64748b',
          callback: (val) => formatCurrency(val),
        },
      },
    },
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Category Breakdown (Donut) */}
      <div className="lg:col-span-5 bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
              <PieChart className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Spending by Category</h3>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            {categories.length} {categories.length === 1 ? 'category' : 'categories'}
          </span>
        </div>

        {categories.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-slate-400 gap-2">
            <Inbox className="w-8 h-8 stroke-1 text-slate-300" />
            <p className="text-xs font-medium">No category spending recorded for this selection.</p>
          </div>
        ) : (
          <div className="relative h-72 flex items-center justify-center">
            <Doughnut data={doughnutData} options={doughnutOptions} />
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-12">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Total
              </span>
              <span className="text-lg font-bold text-slate-800">
                {formatCurrency(total_spending)}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Monthly Trends (Bar Chart) */}
      <div className="lg:col-span-7 bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
              <TrendingUp className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 text-base">Monthly Spending Trends</h3>
              <p className="text-xs text-slate-500">Historical spending trajectory over time</p>
            </div>
          </div>
          <span className="text-xs font-medium text-slate-500">
            {monthly_trends.length} {monthly_trends.length === 1 ? 'Month' : 'Months'}
          </span>
        </div>

        {monthly_trends.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-slate-400 gap-2">
            <Inbox className="w-8 h-8 stroke-1 text-slate-300" />
            <p className="text-xs font-medium">No monthly trend data available yet.</p>
          </div>
        ) : (
          <div className="h-72 w-full pt-2">
            <Bar data={barData} options={barOptions} />
          </div>
        )}
      </div>
    </div>
  );
}
