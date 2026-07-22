"""
Verifies the login token Supabase Auth issues to a logged-in user, and
extracts their real user ID from it.

DESIGN CHANGE: an earlier version verified the token's signature locally,
using a shared JWT secret and assuming HS256 signing. This broke with a
real "Invalid authentication token" error, because Supabase has moved to a
newer signing-key system that can use a different algorithm (ES256) by
default on newer projects -- our hardcoded HS256 check rejected perfectly
valid tokens.

Fix: instead of verifying the signature ourselves (which requires knowing
the exact algorithm/key Supabase is currently using -- something that can
change), we ask Supabase's own Auth server directly: "is this token valid,
and whose is it?" This is what Supabase's own documentation recommends for
projects using a shared-secret signing key, and it works regardless of
which signing method is active, since Supabase's server always knows.
"""

import os
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_ANON_KEY must be set in your .env file. "
        "These are the same public-safe values used in the frontend's .env "
        "(Project Settings -> API in Supabase)."
    )


def get_current_user_id(authorization: str = Header(...)) -> uuid.UUID:
    """
    FastAPI dependency: reads the 'Authorization: Bearer <token>' header,
    asks Supabase's Auth server to verify it, and returns the logged-in
    user's ID. Raises 401 if the header is missing or the token is invalid.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        response = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
            timeout=5.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Could not reach auth server: {e}")

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session, please log in again")

    user_data = response.json()
    user_id_str = user_data.get("id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Token missing user identity")

    return uuid.UUID(user_id_str)
