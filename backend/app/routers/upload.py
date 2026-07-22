"""
POST /upload -- accepts a bank statement PDF, parses it, categorizes every
transaction, saves new ones to the database under the LOGGED-IN USER's real
identity, and returns a summary.
"""

import tempfile
import os
import uuid
from typing import Literal

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.services.statement_import import import_and_save_statement

router = APIRouter()


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    statement_format: Literal["relationship_summary", "statement_of_account"] = Form(...),
    password: str | None = Form(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    session: Session = SessionLocal()
    try:
        summary = import_and_save_statement(
            session,
            user_id,
            tmp_path,
            statement_format,
            password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()
        os.unlink(tmp_path)

    return {
        "filename": file.filename,
        **summary,
    }
