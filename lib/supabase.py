# Supabase client configuration
import os
import httpx
from supabase import create_client, Client
from typing import Optional
from lib.cache import cache_get, cache_set, cache_delete

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

AUTH_URL = f"{SUPABASE_URL}/auth/v1"
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"

_supabase_client: Client = None


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("Supabase URL and anon key must be set")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client


def is_allowed_email_domain(email: str) -> bool:
    ALLOWED_DOMAINS = ["novasbe.pt", "unl.pt"]
    if "@" not in email:
        return False
    domain = email.split("@")[1].lower()
    return domain in [d.lower() for d in ALLOWED_DOMAINS]


def _get_headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def _get_auth_headers(access_token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


# Auth functions - still use httpx directly (not using supabase auth)
def signup_via_rest(email: str, password: str, name: str = None, phone: str = None) -> dict:
    headers = _get_headers()
    user_data = {"email": email, "password": password}
    if name or phone:
        user_data["data"] = {"name": name or "", "phone": phone or ""}
    response = httpx.post(
        f"{AUTH_URL}/signup",
        json=user_data,
        headers=headers,
        timeout=10.0
    )
    print(f"Signup REST API response: {response.status_code} - {response.text}")
    return response.json()


def login_via_rest(email: str, password: str) -> dict:
    headers = _get_headers()
    response = httpx.post(
        f"{AUTH_URL}/token?grant_type=password",
        json={"email": email, "password": password},
        headers=headers,
        timeout=10.0
    )
    print(f"Login REST API response: {response.status_code} - {response.text}")
    return response.json()


def logout_via_rest(access_token: str) -> dict:
    headers = _get_auth_headers(access_token)
    response = httpx.post(
        f"{AUTH_URL}/logout",
        json={},
        headers=headers,
        timeout=10.0
    )
    return response.json() if response.text else {}


def get_user_via_rest(access_token: str) -> dict:
    headers = _get_auth_headers(access_token)
    response = httpx.get(f"{AUTH_URL}/user", headers=headers, timeout=5.0)
    if response.status_code == 200:
        return response.json()
    return {}


# Database functions - use Supabase client (connection pooling built-in)
def _build_query(client, table: str, columns: str = "*", filters: dict = None, order: str = None, limit: int = None):
    query = client.table(table).select(columns)
    if filters:
        for key, value in filters.items():
            clean_value = value.replace("eq.", "") if isinstance(value, str) and value.startswith("eq.") else value
            query = query.eq(key, clean_value)
    if order:
        parts = order.split(".")
        col = parts[0]
        direction = parts[1] if len(parts) > 1 else "asc"
        query = query.order(col, desc=(direction == "desc"))
    if limit:
        query = query.limit(limit)
    return query


def rest_select(table: str, filters: dict = None, order: str = None, limit: int = None, columns: str = "*") -> list:
    """Select rows using Supabase client (HTTP connection pooling)"""
    try:
        client = get_db()
        if client is None:
            return []
        query = _build_query(client, table, columns, filters, order, limit)
        result = query.execute()
        if result.data is not None:
            return result.data
        return []
    except Exception as e:
        print(f"REST select error ({table}): {e}")
    return []


def rest_select_auth(table: str, access_token: str, filters: dict = None, order: str = None, limit: int = None, columns: str = "*") -> list:
    """Select rows using user's access token (authenticated)"""
    try:
        client = get_supabase_client()
        if client is None:
            return []
        query = client.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                clean_value = value.replace("eq.", "") if isinstance(value, str) and value.startswith("eq.") else value
                query = query.eq(key, clean_value)
        if order:
            parts = order.split(".")
            col = parts[0]
            direction = parts[1] if len(parts) > 1 else "asc"
            query = query.order(col, desc=(direction == "desc"))
        if limit:
            query = query.limit(limit)
        query = query.headers({"Authorization": f"Bearer {access_token}"})
        result = query.execute()
        if result.data is not None:
            return result.data
        return []
    except Exception as e:
        print(f"REST select auth error ({table}): {e}")
    return []


def rest_insert(table: str, data: dict) -> dict:
    """Insert row using Supabase client"""
    try:
        client = get_db()
        if client is None:
            return {}
        result = client.table(table).insert(data).execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"REST insert error ({table}): {e}")
    return {}


def rest_insert_auth(table: str, access_token: str, data: dict) -> dict:
    """Insert row using authenticated access token"""
    try:
        client = get_supabase_client()
        if client is None:
            return {}
        result = client.table(table).insert(data).headers({"Authorization": f"Bearer {access_token}"}).execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"REST insert auth error ({table}): {e}")
    return {}


def rest_update(table: str, data: dict, filters: dict) -> dict:
    """Update row using Supabase client"""
    try:
        client = get_db()
        if client is None:
            return {}
        query = client.table(table).update(data)
        for key, value in filters.items():
            clean_value = value.replace("eq.", "") if isinstance(value, str) and value.startswith("eq.") else value
            query = query.eq(key, clean_value)
        result = query.execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"REST update error ({table}): {e}")
    return {}


def rest_update_auth(table: str, access_token: str, data: dict, filters: dict) -> dict:
    """Update row using authenticated access token"""
    try:
        client = get_supabase_client()
        if client is None:
            return {}
        query = client.table(table).update(data).headers({"Authorization": f"Bearer {access_token}"})
        for key, value in filters.items():
            clean_value = value.replace("eq.", "") if isinstance(value, str) and value.startswith("eq.") else value
            query = query.eq(key, clean_value)
        result = query.execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"REST update auth error ({table}): {e}")
    return {}


def rest_delete(table: str, filters: dict) -> bool:
    """Delete row using Supabase client"""
    try:
        client = get_db()
        if client is None:
            return False
        query = client.table(table).delete()
        for key, value in filters.items():
            clean_value = value.replace("eq.", "") if isinstance(value, str) and value.startswith("eq.") else value
            query = query.eq(key, clean_value)
        result = query.execute()
        return True
    except Exception as e:
        print(f"REST delete error ({table}): {e}")
    return False


# Supabase client singleton
supabase: Client = None


def init_supabase():
    global supabase
    try:
        supabase = get_supabase_client()
        print(f"Supabase initialized: {SUPABASE_URL}")
    except Exception as e:
        print(f"Error initializing Supabase: {e}")
        supabase = None
    return supabase


def get_db():
    global supabase
    if supabase is None:
        init_supabase()
    return supabase


def get_storage_transform_url(public_url: str, width: int = 400, height: int = 300) -> str:
    """Add Supabase Storage transformation params to URL for resized thumbnails."""
    if not public_url or "/storage/" not in public_url:
        return public_url
    return f"{public_url}?width={width}&height={height}&resize=cover"


def upload_image(file_data: bytes, file_name: str, bucket: str = "listing-images", access_token: str = None) -> Optional[str]:
    """Upload image to Supabase Storage and return public URL"""
    import uuid

    file_ext = file_name.split('.')[-1].lower() if '.' in file_name else 'jpg'
    if file_ext == 'jpg':
        file_ext = 'jpeg'

    storage_path = f"{uuid.uuid4()}.{file_ext}"
    auth_token = access_token if access_token else SUPABASE_ANON_KEY

    headers = {
        "apikey": auth_token,
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": f"image/{file_ext}",
        "x-upsert": "true"
    }

    try:
        response = httpx.post(
            f"{STORAGE_URL}/object/{bucket}/{storage_path}",
            content=file_data,
            headers=headers,
            timeout=30.0
        )
        if response.status_code in [200, 201]:
            return f"{STORAGE_URL}/object/public/{bucket}/{storage_path}"
    except Exception as e:
        print(f"Image upload error: {e}")

    return None


def invalidate_cache(key_pattern: str = None):
    """Invalidate cache entries. If key_pattern is None, clears all."""
    if key_pattern is None:
        cache_clear()
    else:
        keys_to_delete = [k for k in _cache.keys() if key_pattern in k]
        for k in keys_to_delete:
            cache_delete(k)
