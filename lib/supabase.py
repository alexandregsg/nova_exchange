# Supabase client configuration
import os
import httpx
from supabase import create_client, Client
from typing import Optional
from lib.cache import cache_get, cache_set, cache_delete, cache_clear

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

AUTH_URL = f"{SUPABASE_URL}/auth/v1"
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"

_http_client: httpx.Client = None


def get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=10.0)
    return _http_client


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


def signup_via_rest(email: str, password: str, name: str = None, phone: str = None) -> dict:
    headers = _get_headers()
    user_data = {"email": email, "password": password}
    if name or phone:
        user_data["data"] = {"name": name or "", "phone": phone or ""}
    response = get_http_client().post(
        f"{AUTH_URL}/signup",
        json=user_data,
        headers=headers
    )
    print(f"Signup REST API response: {response.status_code} - {response.text}")
    return response.json()


def login_via_rest(email: str, password: str) -> dict:
    headers = _get_headers()
    response = get_http_client().post(
        f"{AUTH_URL}/token?grant_type=password",
        json={"email": email, "password": password},
        headers=headers
    )
    print(f"Login REST API response: {response.status_code} - {response.text}")
    return response.json()


def logout_via_rest(access_token: str) -> dict:
    headers = _get_auth_headers(access_token)
    response = get_http_client().post(
        f"{AUTH_URL}/logout",
        json={},
        headers=headers
    )
    return response.json() if response.text else {}


def get_user_via_rest(access_token: str) -> dict:
    headers = _get_auth_headers(access_token)
    response = get_http_client().get(f"{AUTH_URL}/user", headers=headers)
    if response.status_code == 200:
        return response.json()
    return {}


def rest_select(table: str, filters: dict = None, order: str = None, limit: int = None, columns: str = "*") -> list:
    """Select rows using pooled HTTP client"""
    params = [f"select={columns}"]
    if filters:
        for key, value in filters.items():
            if isinstance(value, str) and value.startswith("eq."):
                params.append(f"{key}={value}")
            else:
                params.append(f"{key}=eq.{value}")
    if order:
        params.append(f"order={order}")
    if limit:
        params.append(f"limit={limit}")

    query_string = "&".join(params)
    url = f"{REST_URL}/{table}?{query_string}"

    try:
        response = get_http_client().get(url, headers=_get_headers())
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"REST select error ({table}): {e}")
    return []


def rest_select_auth(table: str, access_token: str, filters: dict = None, order: str = None, limit: int = None, columns: str = "*") -> list:
    """Select rows using user's access token (authenticated)"""
    params = [f"select={columns}"]
    if filters:
        for key, value in filters.items():
            if isinstance(value, str) and value.startswith("eq."):
                params.append(f"{key}={value}")
            else:
                params.append(f"{key}=eq.{value}")
    if order:
        params.append(f"order={order}")
    if limit:
        params.append(f"limit={limit}")

    query_string = "&".join(params)
    url = f"{REST_URL}/{table}?{query_string}"

    try:
        response = get_http_client().get(url, headers=_get_auth_headers(access_token))
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"REST select auth error ({table}): {e}")
    return []


def rest_insert(table: str, data: dict) -> dict:
    """Insert row using pooled HTTP client"""
    url = f"{REST_URL}/{table}"
    try:
        response = get_http_client().post(url, json=data, headers=_get_headers())
        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST insert error ({table}): {e}")
    return {}


def rest_insert_auth(table: str, access_token: str, data: dict) -> dict:
    """Insert row using authenticated access token"""
    url = f"{REST_URL}/{table}"
    try:
        response = get_http_client().post(url, json=data, headers=_get_auth_headers(access_token))
        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST insert auth error ({table}): {e}")
    return {}


def rest_update(table: str, data: dict, filters: dict) -> dict:
    """Update row using pooled HTTP client"""
    filter_parts = []
    for key, value in filters.items():
        if isinstance(value, str) and value.startswith("eq."):
            filter_parts.append(f"{key}={value}")
        else:
            filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"

    try:
        response = get_http_client().patch(url, json=data, headers=_get_headers())
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST update error ({table}): {e}")
    return {}


def rest_update_auth(table: str, access_token: str, data: dict, filters: dict) -> dict:
    """Update row using authenticated access token"""
    filter_parts = []
    for key, value in filters.items():
        if isinstance(value, str) and value.startswith("eq."):
            filter_parts.append(f"{key}={value}")
        else:
            filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"

    try:
        response = get_http_client().patch(url, json=data, headers=_get_auth_headers(access_token))
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST update auth error ({table}): {e}")
    return {}


def rest_delete(table: str, filters: dict) -> bool:
    """Delete row using pooled HTTP client"""
    filter_parts = []
    for key, value in filters.items():
        filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"

    try:
        response = get_http_client().delete(url, headers=_get_headers())
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"REST delete error ({table}): {e}")
    return False


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
    if not public_url or "/storage/" not in public_url:
        return public_url
    return f"{public_url}?width={width}&height={height}&resize=cover"


def upload_image(file_data: bytes, file_name: str, bucket: str = "listing-images", access_token: str = None) -> Optional[str]:
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
        response = get_http_client().post(
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
        from lib.cache import _cache
        keys_to_delete = [k for k in _cache.keys() if key_pattern in k]
        for k in keys_to_delete:
            cache_delete(k)
