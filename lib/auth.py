# Authentication utilities
from typing import Optional
from fastapi import Request, HTTPException, status
from lib.supabase import get_user_via_rest, SUPABASE_ANON_KEY, AUTH_URL
import httpx


def get_current_user_via_rest(access_token: str) -> Optional[dict]:
    """Get current user using REST API"""
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
    """Get current user from request cookies - with request-level caching."""
    # Check if already cached on this request
    if hasattr(request.state, "_cached_user"):
        return request.state._cached_user
    
    access_token = request.cookies.get("sb-access-token")
    refresh_token = request.cookies.get("sb-refresh-token")
    
    if not access_token:
        return None
    
    user = get_current_user_via_rest(access_token)
    
    # Cache for this request lifetime
    if user:
        request.state._cached_user = user
    
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