"""
POST /upload -- accepts a bank statement PDF, parses it, categorizes every
transaction, saves new ones to the database under the LOGGED-IN USER's real
identity, and returns a summary.

Duplicate-file protection: before doing any parsing/categorization work, we
hash the raw file bytes and check if this exact file was already uploaded
by this user. If so, we reject it immediately with a clear message,
instead of silently re-processing every transaction only to discover
they're all duplicates (wasted work, and a confusing "0 inserted" result
with no explanation of why).
"""

import hashlib
import tempfile
import os
import uuid
from typing import Literal

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.services.statement_import import import_and_save_statement
from app.models.uploaded_file import UploadedFile

router = APIRouter()


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    statement_format: Literal["relationship_summary", "statement_of_account", "hdfc"] = Form(...),
    password: str | None = Form(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    session: Session = SessionLocal()
    try:
        existing = session.execute(
            select(UploadedFile).where(
                UploadedFile.user_id == user_id,
                UploadedFile.file_hash == file_hash,
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"You've already uploaded this exact file "
                    f"(as '{existing.filename}' on {existing.uploaded_at.strftime('%d %b %Y')}). "
                    "No need to upload it again."
                ),
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

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
            os.unlink(tmp_path)

        # Only record the file hash AFTER a successful import -- if parsing
        # failed (e.g. wrong password), we want the user to be able to
        # retry with the same file, not have it silently blocked.
        session.add(UploadedFile(user_id=user_id, file_hash=file_hash, filename=file.filename))
        session.commit()

    finally:
        session.close()

    return {
        "filename": file.filename,
        **summary,
    }