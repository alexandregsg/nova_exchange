# Profiles API - User profile management
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select, rest_select_auth, rest_insert, rest_update, rest_update_auth, invalidate_cache
from lib.cache import cache_get, cache_set


class ProfileInput(BaseModel):
    user_id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    show_phone: bool = False


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    show_phone: Optional[bool] = None


def get_profile_by_id(id: str) -> Optional[dict]:
    results = rest_select("profiles", filters={"id": f"eq.{id}"})
    return results[0] if results else None


def update_profile(input: ProfileUpdate, user_id: str) -> Optional[dict]:
    update_data = {k: v for k, v in input.model_dump().items() if v is not None}
    if not update_data:
        return None
    result = rest_update("profiles", update_data, {"user_id": f"eq.{user_id}"})
    if result:
        invalidate_cache(f"profile:{user_id}")
    return result


def get_profile_by_user_id(user_id: str, access_token: str = None) -> Optional[dict]:
    """Get profile by user_id - uses auth token if provided. Cached for 5 minutes."""
    cache_key = f"profile:{user_id}"

    if access_token:
        results = rest_select_auth("profiles", access_token, filters={"user_id": f"eq.{user_id}"},
                                    columns="id,user_id,name,avatar_url,bio,phone,show_phone,created_at")
    else:
        results = rest_select("profiles", filters={"user_id": f"eq.{user_id}"},
                               columns="id,user_id,name,avatar_url,bio,phone,show_phone,created_at")

    if results:
        profile = results[0]
        cache_set(cache_key, profile, ttl=300)
        return profile

    return None


def ensure_profile(user_id: str, access_token: str = None) -> dict:
    """Ensure profile exists for user, create if not"""
    print(f"DEBUG ensure_profile: checking for user_id = {user_id}")
    
    # Try to get existing profile first
    existing = get_profile_by_user_id(user_id, access_token)
    if existing:
        print(f"DEBUG ensure_profile: profile found")
        return existing
    
    print(f"DEBUG ensure_profile: profile not found, creating new one")
    
    # Create new profile
    try:
        result = rest_insert("profiles", {
            "user_id": user_id,
            "name": "",
            "show_phone": False
        })
        print(f"DEBUG ensure_profile: insert result = {result}")
        
        # If we get 409 (duplicate), profile was created by someone else - fetch it
        if not result:
            # Try to get again after insert attempt
            existing = get_profile_by_user_id(user_id, access_token)
            if existing:
                print(f"DEBUG ensure_profile: fetched after insert attempt")
                return existing
        
        return result if result else {}
    except Exception as e:
        print(f"DEBUG ensure_profile: error creating profile: {e}")
        return {}


def create_profile(input: ProfileInput) -> dict:
    return rest_insert("profiles", input.model_dump())


def get_all_profiles() -> List[dict]:
    return rest_select("profiles")