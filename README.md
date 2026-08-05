# Smart Budget Analyzer

An AI-powered personal finance analytics platform that ingests bank statement PDFs, automatically categorizes and analyzes spending, detects unusual transactions, forecasts next month's spend, and gets smarter the more you use it.

**Live app**: https://your-app.vercel.app *(replace with your real Vercel URL)*

> Note: the backend runs on Google Cloud Run's free tier, which spins down after periods of inactivity. The first request after some idle time may take 10-20 seconds to wake up — this is expected, not a bug.

---

## What it does

Upload a bank statement PDF and the app will:

- **Parse and categorize** every transaction automatically, learning your specific merchants over time
- **Detect recurring payments** (rent, subscriptions) using amount + interval consistency, correctly distinguishing a monthly bill from a merely-frequent habit like food delivery
- **Flag anomalous transactions** using an Isolation Forest model, comparing each transaction to that specific merchant's own historical pattern (not a blanket amount threshold) so recurring bills aren't falsely flagged
- **Forecast next month's spending** per category using linear regression on trend data, falling back to a simple average when there isn't enough history for a trend to be meaningful
- **Predict a monthly surplus or shortfall** against your self-reported income, with optimization suggestions framed against your own historical baseline rather than a countdown-style "budget remaining" number (a countdown framing has been shown in behavioral economics research to encourage *more* spending near the end of a period)
- **Learn from you**: click any flagged transaction to categorize it (including creating entirely custom categories) or exclude a merchant from anomaly detection — corrections apply retroactively to past transactions, not just future ones
- **Visualize everything**: monthly category trends, a "this month vs. all time" pie chart, cash flow (income vs. expense), top merchants, a spending-by-day-of-month heatmap, and a scatter plot of the actual feature space the anomaly detection model evaluates

## Screenshots

*(Add screenshots here — Hero page, Dashboard, Upload flow)*

---

## Tech Stack

**Backend**
- FastAPI (Python)
- SQLAlchemy + PostgreSQL (hosted on Supabase)
- scikit-learn (Isolation Forest for anomaly detection)
- pandas, pdfplumber, pypdf (statement parsing)
- Supabase Auth (verified server-side against Supabase's Auth API)
- Deployed on Google Cloud Run (Docker)

**Frontend**
- React + Vite
- Tailwind CSS v4
- Recharts (all charts and visualizations)
- Supabase JS client (authentication)
- Deployed on Vercel

**Database & Auth**
- Supabase (managed PostgreSQL + authentication, email/password and Google OAuth)

---

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   React     │──────▶│    FastAPI       │──────▶│  Supabase   │
│  (Vercel)   │◀──────│  (Cloud Run)     │◀──────│  Postgres   │
└─────────────┘      └──────────────────┘      └─────────────┘
       │                                              ▲
       └──────────── Supabase Auth ───────────────────┘
              (login/signup, token verification)
```

Every request to the backend carries a Supabase-issued login token, which the backend verifies directly against Supabase's Auth server on each call — rather than trusting a locally-decoded signature — so it stays correct regardless of which signing method Supabase uses under the hood.

---

## Key design decisions

A few choices worth calling out, since they came from real debugging and research rather than defaults:

- **Anomaly detection compares each transaction to its own merchant's historical pattern**, not a global amount threshold. A naive approach would flag a ₹5,800 rent payment as anomalous every month simply because it's larger than most transactions — the model instead measures deviation from *that specific merchant's* own typical amount.
- **Recurring payment detection requires both amount AND interval consistency**, and explicitly excludes very-frequent merchants (daily food delivery, cab rides) from being mistaken for a monthly bill — a bill isn't suspicious just for happening less often than a daily habit.
- **Forecasting falls back to a simple average with fewer than 3 months of data**, rather than fitting a trend line to 1-2 points, which would just be noise presented as a prediction.
- **Budget recommendations avoid a "money remaining" framing.** Research on budgeting apps has found that showing a remaining-budget number can *increase* spending late in the period, since it reframes the remainder as "safe to spend." Recommendations here compare current spend to the user's own historical average instead.
- **Merchant descriptions are normalized before categorization**, stripping bank codes, transaction IDs, and UPI handle noise — categorization accuracy is bottlenecked by description quality more than by the classifier itself.

---

## Project Structure

```
finance-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── auth.py              # Supabase token verification
│   │   ├── db.py                # SQLAlchemy engine/session setup
│   │   ├── routers/             # API endpoints
│   │   ├── parsers/             # Bank statement PDF parsers
│   │   ├── categorization/      # Rules engine + personalization
│   │   ├── analytics/           # Trends, recurring, forecasting, anomalies, budget
│   │   ├── models/              # SQLAlchemy models
│   │   └── services/            # Shared business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Dashboard, Upload, Login, charts
│   │   ├── context/              # Auth state
│   │   ├── api/                  # Backend API client
│   │   └── utils/
│   └── package.json
└── render.yaml                   # Alternate deployment config (Render)
```

---

## Running Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your own Supabase + database values
python init_db.py
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # fill in your own Supabase values
npm run dev
```

### Required environment variables

**Backend** (`backend/.env`):
| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string (Supabase) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `ALLOWED_ORIGINS` | Comma-separated frontend URL(s) allowed via CORS (omit for local dev) |

**Frontend** (`frontend/.env`):
| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon/public key |
| `VITE_API_URL` | Deployed backend URL (omit for local dev — falls back to the Vite proxy) |

---

## Status

Actively developed. Supported statement formats: SBI "Relationship Summary" and "Statement of Account" layouts, including password-protected PDFs.

## License

MIT