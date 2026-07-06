"""
Quick connectivity test -- run this BEFORE building any real tables, just
to confirm the connection to Supabase actually works.

Usage: python test_db_connection.py
"""

from sqlalchemy import text

from app.db import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.scalar()
        print("Connection successful!")
        print(f"Postgres version: {version}")
except Exception as e:
    print("Connection FAILED.")
    print(f"Error: {e}")
