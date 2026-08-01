import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import upload, analyze, budget, visualizations, personalization, coverage

load_dotenv()

app = FastAPI(
    title="Smart Budget Analyzer API",
    description="Ingests bank statements and returns personalized spending analytics.",
    version="0.1.0",
)

# Locked down via the ALLOWED_ORIGINS env var once deployed (comma-separated
# list of real frontend URLs). Falls back to "*" for local development, since
# there's no real domain to lock to yet when running on localhost.
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
allowed_origins = allowed_origins_env.split(",") if allowed_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(budget.router)
app.include_router(visualizations.router)
app.include_router(personalization.router)
app.include_router(coverage.router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Smart Budget Analyzer API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
