"""
One message (user question or assistant answer) inside a ChatConversation.
Only final Q/A pairs are stored here -- the intermediate tool-use round
trips that happen inside a single turn (asking for get_anomalies(), etc.)
are NOT persisted, so every new question re-runs fresh tool calls against
current data rather than replaying stale results.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_conversations.id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)