"""
POST /chat -- ask a question, grounded in your own computed analytics via
tool use against Groq's llama-3.3-70b-versatile. Pass conversation_id to
continue an existing thread, or omit it to start a new one.
GET /chat/conversations -- list your past conversations
GET /chat/conversations/{id} -- full message history for one conversation
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.llm.chat_service import run_chat_turn

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


@router.post("/chat")
def chat(body: ChatRequest, user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        if body.conversation_id is not None:
            conversation = session.get(ChatConversation, body.conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise HTTPException(status_code=404, detail="Conversation not found")
        return run_chat_turn(session, user_id, body.message, body.conversation_id)
    finally:
        session.close()


@router.get("/chat/conversations")
def list_conversations(user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        conversations = (
            session.query(ChatConversation)
            .filter(ChatConversation.user_id == user_id)
            .order_by(ChatConversation.created_at.desc())
            .all()
        )
        return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in conversations]
    finally:
        session.close()


@router.get("/chat/conversations/{conversation_id}")
def get_conversation(conversation_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        conversation = session.get(ChatConversation, conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]
    finally:
        session.close()