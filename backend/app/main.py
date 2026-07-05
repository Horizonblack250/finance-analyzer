"""
Smart Budget Analyzer - FastAPI backend entrypoint.

This app exposes REST endpoints for:
- Uploading bank statements (CSV/PDF)
- Retrieving parsed & categorized transactions
- Fetching analytics (trends, recurring payments, forecasts, anomalies)
- Getting personalized spending recommendations

Run locally with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Smart Budget Analyzer API",
    description="Ingests bank statements and returns personalized spending analytics.",
    version="0.1.0",
)

# Allow the React frontend (running on a different port/domain) to call this API.
# In production, replace "*" with your actual deployed frontend URL for security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """Basic health check endpoint."""
    return {"status": "ok", "message": "Smart Budget Analyzer API is running"}


@app.get("/health")
def health_check():
    """Used by hosting platforms (Render, etc.) to verify the service is alive."""
    return {"status": "healthy"}
