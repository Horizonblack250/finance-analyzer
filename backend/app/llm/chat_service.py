"""
The tool-use loop: send the user's question + conversation history + tool
schemas to an LLM provider, walking a fallback chain if one fails. If the
model asks for a tool, run it against this user's real data and feed the
result back. Repeat until the model gives a final text answer.

FALLBACK CHAIN DESIGN (inspired by the Mimir project's provider_chains
pattern): each entry is an independent OpenAI-compatible provider. On any
error, we move to the next provider in the chain rather than failing the
whole request. This differs from Mimir's own call_model() in one important
way: that function only ever returns final text and drops tool_calls
entirely, which would silently break tool-calling here -- this version
checks for and returns tool calls explicitly, since the entire chat
feature depends on them.

Only the final user question and final assistant answer get saved to the
DB (see chat_message.py docstring for why).
"""

import json
import os
import uuid

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.llm.tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

MAX_TOOL_ROUNDS = 5

# Ordered fallback chain -- tried top to bottom. Each entry needs its API
# key env var actually set to be attempted; missing keys are skipped
# silently rather than causing an error, so this works fine even before
# every provider below is configured.
PROVIDER_CHAIN = [
    {
        "name": "groq-gpt-oss-120b",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
    },
    {
        "name": "gemini-3.6-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-3.6-flash",
    },
]

SYSTEM_PROMPT = (
    "You are a personal finance assistant inside a budgeting app. Answer "
    "the user's question about their own spending using ONLY the tools "
    "provided -- never guess or make up numbers. Call whichever tools are "
    "relevant, possibly more than one, before answering. Keep answers "
    "concise and concrete, referencing actual figures from the tool "
    "results. If the tools don't contain enough information to answer, "
    "say so directly instead of speculating.\n\n"
    "IMPORTANT: All monetary amounts in the tool results are in Indian "
    "Rupees (INR), not US Dollars. Always format amounts using the ₹ "
    "symbol (e.g. ₹50,506.95), never $ or 'USD'."
)


def _call_with_fallback(messages: list[dict]):
    """
    Walks PROVIDER_CHAIN in order. Returns (response, provider_name) from
    the first provider that succeeds. Raises RuntimeError only if every
    provider in the chain fails or is unconfigured.
    """
    last_error = None
    for provider in PROVIDER_CHAIN:
        api_key = os.getenv(provider["api_key_env"])
        if not api_key:
            continue
        try:
            client = OpenAI(api_key=api_key, base_url=provider["base_url"])
            response = client.chat.completions.create(
                model=provider["model"],
                messages=messages,
                tools=TOOL_SCHEMAS,
            )
            return response, provider["name"]
        except Exception as e:
            print(f"[fallback chain] {provider['name']} failed: {type(e).__name__}: {e}")
            last_error = e
            continue

    raise RuntimeError(
        f"All providers in the fallback chain failed or are unconfigured. "
        f"Last error: {last_error}"
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
    title_override: str | None = None,
) -> dict:
    if conversation_id is None:
        conversation = ChatConversation(
            user_id=user_id, title=title_override or user_message[:60]
        )
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
            response, provider_name = _call_with_fallback(working_messages)
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
    except RuntimeError:
        final_text = (
            "I couldn't reach any of my language model providers just now -- "
            "give it a moment and try again."
        )

    if final_text is None:
        final_text = (
            "I wasn't able to finish looking that up -- try rephrasing your "
            "question or asking about something more specific."
        )

    session.add(ChatMessage(conversation_id=conversation_id, role="assistant", content=final_text))
    session.commit()

    return {"conversation_id": conversation_id, "reply": final_text}