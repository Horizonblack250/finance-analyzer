"""
Tracks which exact files a user has already uploaded, identified by a hash
of the file's actual bytes (not just the filename -- someone could rename
a file, and this still catches it; two genuinely different files with the
same name are still treated as different uploads).

This lets us reject a re-upload of the same statement immediately, before
wasting time parsing it and running every transaction through
categorization just to discover they're all duplicates.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (UniqueConstraint("user_id", "file_hash", name="uq_user_file_hash"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    file_hash = Column(String, nullable=False)
    filename = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
