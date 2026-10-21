# Personal Expense Analyzer 💸

A modern, full-stack personal finance application for recording expenses, monitoring spending habits, visualizing monthly trends, tracking payment channels, and exporting financial statements. Tailored for Indian users with consistent **₹ (INR)** formatting.

Built with a **FastAPI** (Python) backend and a **React + Vite + Tailwind CSS** frontend.

---

## 🌟 Key Features

- **Dashboard Financial KPIs**: Instant visibility into Total Spending, Number of Expenses, Average Expense, and Top Category in Indian Rupees (`₹`).
- **Interactive Visualizations**:
  - **Category Breakdown**: Doughnut chart showing percentage and Rupee share per spending category.
  - **Monthly Trends**: Bar chart highlighting spending patterns across recent months.
- **Bulk Expense Selection & Deletion**:
  - Row checkboxes and a master "Select All" with native indeterminate state.
  - Floating action bar showing selected count and combined total in `₹`.
  - Dedicated confirmation modal requiring user approval before permanently deleting selected items.
- **Data Export (CSV & Excel)**:
  - **Expenses (CSV)**: Formatted with UTF-8 BOM (`\ufeff`) so the `₹` Rupee symbol renders cleanly in Excel.
  - **Expenses (Excel `.xlsx`)**: Styled spreadsheets with auto-sized columns and highlighted headers.
  - **Financial Summary Reports**: Export overall KPIs, category breakdowns, and payment method statistics as CSV or Excel.
- **Date Filters & Period Comparisons**:
  - Filter by Month, Calendar Quarter (Q1–Q4), Year, or Custom Date Range (`Start Date` to `End Date`).
  - **Period-over-Period Comparison Card**: Compare spending between two periods (Monthly, Quarterly, Yearly) with net change in `₹`, % variance, and category-level shift breakdown.
- **Payment Method Breakdown**:
  - Dedicated visual cards and progress meters for **UPI Payments**, **Cash**, **Credit Card**, **Debit Card**, and **Bank Transfer / NetBanking**.
- **Monthly Summary Override**:
  - Record an official monthly total from bank statements to avoid double-counting unitemized expenses while preserving individual receipt history.

---

## 📁 Project Structure

```
itr/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py       # SQLAlchemy connection (supports SQLite & PostgreSQL)
│   │   ├── models.py         # Database ORM models
│   │   ├── schemas.py        # Pydantic validation schemas
│   │   ├── crud.py           # Queries, aggregations, and bulk operations
│   │   ├── seed.py           # Sample expenses auto-seeding
│   │   └── main.py           # FastAPI entrypoint, routes, and CORS
│   ├── .env.example          # Sample backend environment configuration
│   ├── requirements.txt      # Python dependencies (FastAPI, uvicorn, openpyxl, psycopg2)
│   └── test_api.py           # Automated unit test suite
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── expenses.js   # API client communicating with FastAPI
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── SummaryCards.jsx
│   │   │   ├── PaymentSummaryCards.jsx
│   │   │   ├── ComparisonCard.jsx
│   │   │   ├── ChartSection.jsx
│   │   │   ├── FilterBar.jsx
│   │   │   ├── ExpenseTable.jsx
│   │   │   ├── ExpenseModal.jsx
│   │   │   ├── DeleteConfirmModal.jsx
│   │   │   ├── BulkDeleteConfirmModal.jsx
│   │   │   ├── MonthlySummaryModal.jsx
│   │   │   ├── MonthlySummaryBanner.jsx
│   │   │   └── Toast.jsx
│   │   ├── utils/
│   │   │   └── currency.js   # Indian Rupee (₹) formatting utility
│   │   ├── App.jsx           # Main dashboard container
│   │   ├── main.jsx
│   │   └── index.css         # Tailwind directives
│   ├── .env.example          # Sample frontend environment configuration
│   ├── vercel.json           # Vercel SPA routing rewrites configuration
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── .gitignore                # Protects secrets, node_modules, and database files
├── render.yaml               # Render Blueprint deployment specification
├── DEPLOYMENT.md             # Detailed production deployment checklist
└── README.md
```

---

## 💻 Local Quick Start (Windows PowerShell)

### Prerequisites
- **Python 3.10+** (`python --version`)
- **Node.js 18+** & **npm** (`node -v` and `npm.cmd -v`)

> [!NOTE]
> On Windows PowerShell, always invoke `npm.cmd` instead of bare `npm` to bypass PowerShell script execution policy restrictions.

### 1. Run the Backend Server
```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Root: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 2. Run the Frontend Application
Open a second PowerShell window:
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
- Frontend Web App: [http://localhost:5173](http://localhost:5173)

---

## 🚀 Production Deployment Guide

This project is pre-configured for seamless production deployment with **Vercel** (Frontend) and **Render** (Backend).

---

### Step 1: Deploy Backend to Render

1. Create a free account at [render.com](https://render.com).
2. Click **New +** > **Web Service** and connect your GitHub repository.
3. Configure the service settings:
   - **Name**: `personal-expense-analyzer-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In the **Environment Variables** section, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `CORS_ORIGINS`: `https://your-frontend-app.vercel.app` *(or leave blank; all `*.vercel.app` domains are automatically allowed)*

---

### ⚠️ Critical: Database Persistence on Render

> [!WARNING]
> **Render's Free Web Services have an ephemeral filesystem!**
> If you run SQLite in the default container directory on the free tier, the database file will be deleted whenever the container restarts or spins down due to inactivity.

To ensure your financial records and expenses persist permanently in production, choose one of the following two safe options:

#### Option A: Managed PostgreSQL (Recommended for Free Tier)
1. On Render, click **New +** > **PostgreSQL**.
2. Create a free PostgreSQL instance (e.g. `expense-db`).
3. Copy the **Internal Database URL** (or External Database URL).
4. In your backend Web Service's **Environment Variables**, add:
   - **Key**: `DATABASE_URL`
   - **Value**: `postgresql://user:password@host/dbname`
5. The backend will automatically detect `DATABASE_URL`, initialize tables, and persist all data permanently without data loss.

#### Option B: Render Persistent Disk (Paid Starter Tier)
1. Upgrade your Web Service instance type from Free to **Starter** ($7/mo).
2. Under the service's **Disks** tab, click **Add Disk**:
   - **Name**: `expense-data`
   - **Mount Path**: `/var/data`
   - **Size**: `1 GB`
3. In **Environment Variables**, set:
   - **Key**: `DATABASE_FILE`
   - **Value**: `/var/data/expenses.db`
4. The database file will now be stored on the persistent disk and will survive all deployments and container restarts.

---

### Step 2: Deploy Frontend to Vercel

1. Create a free account at [vercel.com](https://vercel.com).
2. Click **Add New...** > **Project** and import your GitHub repository.
3. In the project setup screen, configure:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select **`frontend`**
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
4. Under **Environment Variables**, add:
   - **NAME**: `VITE_API_URL`
   - **VALUE**: `https://<your-render-backend-name>.onrender.com` *(your deployed Render backend URL, without a trailing slash)*
5. Click **Deploy**. Vercel will build and launch your site with a custom `https://<your-app>.vercel.app` domain.
6. The included [vercel.json](file:///c:/Users/Dell/OneDrive/Desktop/itr/frontend/vercel.json) automatically handles SPA rewrites so direct navigation and refreshes never 404.

---

### Step 3: Verify the Deployment

1. Visit `https://<your-render-backend-name>.onrender.com/api/health` in your browser. It should respond with `{"status":"healthy"}`.
2. Visit `https://<your-render-backend-name>.onrender.com/docs` to inspect interactive Swagger documentation.
3. Open your deployed Vercel site `https://<your-app>.vercel.app`:
   - Verify expenses load from the backend.
   - Test adding, selecting, and bulk deleting expenses.
   - Test downloading CSV and Excel reports.
   - Test filtering by date, quarter, and payment method.

---

## 🔒 Security & Best Practices

- **Zero Secrets in Code**: No API keys, passwords, or credentials are hardcoded.
- **Git Protection**: The included [.gitignore](file:///c:/Users/Dell/OneDrive/Desktop/itr/.gitignore) ensures `.env`, `node_modules`, `dist`, Python caches, and local `*.db` files are never exposed in version control.
- **CORS Protection**: The backend accepts requests from local development ports, all Vercel domains (`https://*.vercel.app`), and custom domains specified in the `CORS_ORIGINS` environment variable.

---

## 🧪 Automated Testing

Run the automated backend test suite locally before pushing changes:
```powershell
cd backend
python test_api.py
```
All tests verify table creation, expense CRUD, monthly summary overrides, bulk deletion, and analytical aggregations.
