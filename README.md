# Smart Budget Analyzer

An AI-powered personal finance analytics platform. Upload your bank statements
(a single month or a full year), and it parses, categorizes, and analyzes your
spending — then learns from your corrections over time to give increasingly
personalized insights and recommendations.

## Features (planned)

- [ ] Upload bank statements (CSV, PDF)
- [ ] Automatic transaction categorization (rules + ML)
- [ ] Multi-month consolidated spending trends
- [ ] Recurring payment / subscription detection
- [ ] Spending forecasts (next month, per category)
- [ ] Anomaly detection (unusual spend spikes)
- [ ] Personalized optimization recommendations
- [ ] Feedback loop: user corrections improve the categorization model

## Tech Stack

- **Backend**: FastAPI, PostgreSQL (Supabase), scikit-learn
- **Frontend**: React + Vite, Tailwind CSS, shadcn/ui, Recharts
- **Deployment**: Render (backend), Vercel (frontend), Supabase (database + auth)

## Project Structure

```
backend/
  app/
    main.py          # FastAPI entrypoint
    routers/         # API route handlers
    parsers/         # Bank statement parsers (PDF/CSV -> normalized transactions)
    categorization/  # Rule-based + ML transaction categorization
    analytics/       # Trends, recurring detection, forecasting, anomalies
    models/           # SQLAlchemy DB models
    schemas/          # Pydantic request/response schemas
frontend/
  src/
    pages/
    components/
    api/
```

## Local Development

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API will be running at http://localhost:8000

### Frontend
(Coming in a later step)

## Status

🚧 Actively in development.
