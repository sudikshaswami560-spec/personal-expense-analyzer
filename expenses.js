const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

const TOKEN_KEY = 'pea_auth_token';
const USER_KEY = 'pea_auth_user';

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
  getUser: () => {
    try {
      const u = localStorage.getItem(USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  setUser: (user) => localStorage.setItem(USER_KEY, JSON.stringify(user)),
  clearUser: () => localStorage.removeItem(USER_KEY),
  clearAll: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

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
 * Generic request helper with authentication header and error handling
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = authStorage.getToken();

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    const isJson = res.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await res.json() : await res.text();

    if (!res.ok) {
      if (res.status === 401) {
        // If unauthorized and endpoint is not login/register, clear credentials
        if (!endpoint.includes('/api/auth/')) {
          authStorage.clearAll();
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
      }

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
  // Authentication
  login: async (email, password) => {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    authStorage.setToken(data.access_token);
    authStorage.setUser(data.user);
    return data;
  },
  register: async (email, password, full_name) => {
    const data = await request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    });
    authStorage.setToken(data.access_token);
    authStorage.setUser(data.user);
    return data;
  },
  getMe: () => request('/api/auth/me'),
  logout: () => {
    authStorage.clearAll();
  },

  // Expenses & Metadata
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

  // Authenticated Export Download Helpers
  downloadFile: async (url, filename) => {
    const token = authStorage.getToken();
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      throw new Error('Failed to download exported file');
    }
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  },
  getExportExpensesUrl: (filters = {}, format = 'csv') => {
    const token = authStorage.getToken();
    const params = { ...filters, format, ...(token ? { token } : {}) };
    return `${API_BASE_URL}/api/export/expenses${buildQueryString(params)}`;
  },
  getExportSummaryUrl: (filters = {}, format = 'csv') => {
    const token = authStorage.getToken();
    const baseParams = typeof filters === 'string' ? { month: filters, format } : { ...filters, format };
    const params = { ...baseParams, ...(token ? { token } : {}) };
    return `${API_BASE_URL}/api/export/summary${buildQueryString(params)}`;
  },
  checkHealth: () => request('/api/health'),
};
