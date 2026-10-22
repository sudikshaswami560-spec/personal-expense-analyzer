const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

/**
 * Helper to build clean query string omitting empty or undefined filters
 */
function buildQueryString(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      query.append(key, value);
    }
  }
  const str = query.toString();
  return str ? `?${str}` : '';
}

/**
 * Generic request helper with error handling
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    const isJson = res.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await res.json() : await res.text();

    if (!res.ok) {
      // Extract detailed validation message if provided by FastAPI
      let errorMessage = 'An unexpected error occurred';
      if (typeof data === 'object' && data !== null) {
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((err) => `${err.loc?.slice(-1)[0] || 'field'}: ${err.msg}`).join(', ');
        } else if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (data.message) {
          errorMessage = data.message;
        }
      } else if (typeof data === 'string' && data) {
        errorMessage = data;
      }
      throw new Error(errorMessage);
    }

    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to backend server at ${API_BASE_URL}. Please ensure the FastAPI server is running.`
      );
    }
    throw err;
  }
}

export const api = {
  getExpenses: (filters = {}) => request(`/api/expenses${buildQueryString(filters)}`),
  getSummary: (filters = {}) => request(`/api/analytics/summary${buildQueryString(filters)}`),
  getMetadata: () => request('/api/meta'),
  createExpense: (payload) =>
    request('/api/expenses', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateExpense: (id, payload) =>
    request(`/api/expenses/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteExpense: (id) =>
    request(`/api/expenses/${id}`, {
      method: 'DELETE',
    }),
  getMonthlySummaries: () => request('/api/monthly-summaries'),
  getMonthlySummary: (month) => request(`/api/monthly-summaries/${month}`),
  saveMonthlySummary: (payload) =>
    request('/api/monthly-summaries', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteMonthlySummary: (month) =>
    request(`/api/monthly-summaries/${month}`, {
      method: 'DELETE',
    }),
  bulkDeleteExpenses: (ids) =>
    request('/api/expenses/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),
  getComparison: (params) => request(`/api/analytics/comparison${buildQueryString(params)}`),
  getExportExpensesUrl: (filters = {}, format = 'csv') =>
    `${API_BASE_URL}/api/export/expenses${buildQueryString({ ...filters, format })}`,
  getExportSummaryUrl: (filters = {}, format = 'csv') => {
    const params = typeof filters === 'string' ? { month: filters, format } : { ...filters, format };
    return `${API_BASE_URL}/api/export/summary${buildQueryString(params)}`;
  },
  checkHealth: () => request('/api/health'),
};
