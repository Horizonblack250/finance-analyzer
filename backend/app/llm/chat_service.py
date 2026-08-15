"""
The tool-use loop: send the user's question + conversation history + tool
schemas to Groq's OpenAI-compatible API. If the model asks for a tool, run
it against this user's real data and feed the result back. Repeat until
the model gives a final text answer. Only the final user question and
final assistant answer get saved to the DB (see chat_message.py docstring
for why).
"""

import json
import os
import uuid

from openai import OpenAI, RateLimitError
from sqlalchemy.orm import Session

from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.llm.tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = (
    "You are a personal finance assistant inside a budgeting app. Answer "
    "the user's question about their own spending using ONLY the tools "
    "provided -- never guess or make up numbers. Call whichever tools are "
    "relevant, possibly more than one, before answering. Keep answers "
    "concise and concrete, referencing actual figures from the tool "
    "results. If the tools don't contain enough information to answer, "
    "say so directly instead of speculating."
)

_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)


def _load_history(session: Session, conversation_id: uuid.UUID) -> list[dict]:
    messages = (
        session.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def run_chat_turn(
    session: Session,
    user_id: uuid.UUID,
    user_message: str,
    conversation_id: uuid.UUID | None,
) -> dict:
    if conversation_id is None:
        conversation = ChatConversation(user_id=user_id, title=user_message[:60])
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        conversation_id = conversation.id
        history = []
    else:
        history = _load_history(session, conversation_id)

    session.add(ChatMessage(conversation_id=conversation_id, role="user", content=user_message))
    session.commit()

    working_messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": user_message}]
    )

    final_text = None
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = _client.chat.completions.create(
                model=MODEL,
                messages=working_messages,
                tools=TOOL_SCHEMAS,
            )
            choice = response.choices[0]

            if choice.finish_reason != "tool_calls":
                final_text = choice.message.content
                break

            working_messages.append(choice.message.model_dump(exclude_none=True))

            for tool_call in choice.message.tool_calls:
                func = TOOL_FUNCTIONS.get(tool_call.function.name)
                raw_args = tool_call.function.arguments
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                result = (
                    func(session, user_id, **args)
                    if func is not None
                    else {"error": f"Unknown tool: {tool_call.function.name}"}
                )
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })
    except RateLimitError:
        final_text = (
            "I've hit the free-tier rate limit for the moment -- give it "
            "about a minute and try again."
        )

    if final_text is None:
        final_text = (
            "I wasn't able to finish looking that up -- try rephrasing your "
            "question or asking about something more specific."
        )

    session.add(ChatMessage(conversation_id=conversation_id, role="assistant", content=final_text))
    session.commit()

    return {"conversation_id": conversation_id, "reply": final_text}