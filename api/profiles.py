# Profiles API - User profile management
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select_async, rest_select_auth_async, rest_insert_async, rest_update_async, invalidate_cache
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


async def get_profile_by_id(id: str) -> Optional[dict]:
    results = await rest_select_async("profiles", filters={"id": f"eq.{id}"})
    return results[0] if results else None


async def update_profile(input: ProfileUpdate, user_id: str) -> Optional[dict]:
    update_data = {k: v for k, v in input.model_dump().items() if v is not None}
    if not update_data:
        return None
    result = await rest_update_async("profiles", update_data, {"user_id": f"eq.{user_id}"})
    if result:
        invalidate_cache(f"profile:{user_id}")
    return result


async def get_profile_by_user_id(user_id: str, access_token: str = None) -> Optional[dict]:
    cache_key = f"profile:{user_id}"

    if access_token:
        results = await rest_select_auth_async("profiles", access_token, filters={"user_id": f"eq.{user_id}"},
                                    columns="id,user_id,name,avatar_url,bio,phone,show_phone,created_at")
    else:
        results = await rest_select_async("profiles", filters={"user_id": f"eq.{user_id}"},
                               columns="id,user_id,name,avatar_url,bio,phone,show_phone,created_at")

    if results:
        profile = results[0]
        cache_set(cache_key, profile, ttl=300)
        return profile

    return None


async def ensure_profile(user_id: str, access_token: str = None) -> dict:
    existing = await get_profile_by_user_id(user_id, access_token)
    if existing:
        return existing

    try:
        result = await rest_insert_async("profiles", {
            "user_id": user_id,
            "name": "",
            "show_phone": False
        })

        if not result:
            existing = await get_profile_by_user_id(user_id, access_token)
            if existing:
                return existing

        return result if result else {}
    except Exception as e:
        print(f"ensure_profile error creating profile: {e}")
        return {}


async def create_profile(input: ProfileInput) -> dict:
    return await rest_insert_async("profiles", input.model_dump())


async def get_all_profiles() -> List[dict]:
    return await rest_select_async("profiles")
