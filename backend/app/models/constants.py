"""
Placeholder for the "logged in user" until real auth (Supabase Auth) is
wired up. Every transaction/correction gets tagged with this ID for now,
so the schema is already multi-user-shaped when auth arrives later --
at that point, this constant gets replaced by the actual logged-in user's
ID from the auth session, and nothing else about the schema has to change.
"""

import uuid

# Fixed, arbitrary UUID standing in for "you" until real login exists.
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
