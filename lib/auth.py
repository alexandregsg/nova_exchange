# Authentication utilities
from typing import Optional
from fastapi import Request, HTTPException, status
from lib.supabase import get_user_via_rest_async, SUPABASE_ANON_KEY, AUTH_URL, rest_select_async
import httpx
import time
import threading


_user_cache: dict = {}
_user_cache_lock = threading.Lock()
_USER_CACHE_TTL = 60


def get_current_user_via_rest(access_token: str) -> Optional[dict]:
    """Get current user using REST API (sync - for non-async contexts only)."""
    if not access_token:
        return None

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        response = httpx.get(f"{AUTH_URL}/user", headers=headers, timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"get_current_user error: {e}")

    return None


async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from request cookies - with cross-request caching and profile enrichment."""
    if hasattr(request.state, "_cached_user"):
        return request.state._cached_user

    access_token = request.cookies.get("sb-access-token")
    if not access_token:
        return None

    now = time.time()
    with _user_cache_lock:
        cached = _user_cache.get(access_token)
        if cached and cached["expires"] > now:
            user = cached["user"]
            request.state._cached_user = user
            return user

    user = await get_user_via_rest_async(access_token)

    if user:
        user_id = user.get("id", "")
        if user_id:
            profile_results = await rest_select_async("profiles", filters={"user_id": f"eq.{user_id}"}, columns="name,avatar_url")
            if profile_results:
                profile = profile_results[0]
                user["name"] = profile.get("name") or user.get("email", "").split("@")[0]
                user["avatar_url"] = profile.get("avatar_url")
            else:
                user["name"] = user.get("email", "").split("@")[0] if "@" in user.get("email", "") else "User"
                user["avatar_url"] = None
        request.state._cached_user = user
        with _user_cache_lock:
            _user_cache[access_token] = {"user": user, "expires": now + _USER_CACHE_TTL}
            expired = [k for k, v in _user_cache.items() if v["expires"] <= now]
            for k in expired:
                del _user_cache[k]

    return user


async def require_authentication(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


def is_authenticated(request: Request) -> bool:
    access_token = request.cookies.get("sb-access-token")
    return access_token is not None