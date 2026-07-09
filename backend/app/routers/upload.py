"""
POST /upload -- accepts a bank statement PDF, parses it, categorizes every
transaction, saves new ones to the database, and returns a summary.

This is the real product entrypoint -- the same thing run_categorization.py
and import_statement.py let us test from the command line, now reachable
over HTTP the way an actual frontend will call it.
"""

import tempfile
import os
from typing import Literal

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.services.statement_import import import_and_save_statement

router = APIRouter()


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    statement_format: Literal["relationship_summary", "statement_of_account"] = Form(...),
    password: str | None = Form(None),
):
    # Save the uploaded file to a temp path -- our parsers work off a file
    # path (pdfplumber.open), not an in-memory stream, so this is the
    # simplest bridge between "file arrived over HTTP" and "existing,
    # already-tested parser code".
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    session: Session = SessionLocal()
    try:
        summary = import_and_save_statement(
            session,
            DEFAULT_USER_ID,
            tmp_path,
            statement_format,
            password,
        )
    except ValueError as e:
        # Wrong/missing password, or a parsing error -- surface it clearly
        # instead of a generic 500.
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()
        os.unlink(tmp_path)  # clean up the temp file regardless of outcome

    return {
        "filename": file.filename,
        **summary,
    }
