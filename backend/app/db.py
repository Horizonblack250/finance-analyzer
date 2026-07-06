"""
Database connection setup.

Reads DATABASE_URL from the .env file (never committed to git -- see
.gitignore). Converts the standard "postgresql://" URL Supabase gives you
into the "postgresql+psycopg://" form SQLAlchemy needs to use the psycopg3
driver, so you don't have to edit your .env file yourself.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

_raw_url = os.getenv("DATABASE_URL")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Make sure you have a .env file in the "
        "backend/ folder with a line like: DATABASE_URL=postgresql://..."
    )

# SQLAlchemy needs the driver named explicitly in the URL scheme when using
# psycopg3. Supabase gives you a plain "postgresql://" URL, so we rewrite it.
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = _raw_url

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session, closes it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
