# Supabase client configuration
import os
import threading
import httpx
from httpx import Limits
from supabase import create_client, Client
from typing import Optional
from lib.cache import cache_get, cache_set, cache_delete, cache_clear

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

AUTH_URL = f"{SUPABASE_URL}/auth/v1"
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"

_http_client: httpx.Client = None
_http_async_client: httpx.AsyncClient = None
_supabase_client: Client = None

_init_lock = threading.Lock()
_async_init_lock = threading.Lock()
_supabase_lock = threading.Lock()

# Pre-build headers dict once at module load (SUPABASE_ANON_KEY is constant)
_ANON_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        with _init_lock:
            if _http_client is None:
                _http_client = httpx.Client(
                    timeout=10.0,
                    limits=Limits(max_keepalive_connections=20, max_connections=100)
                )
    return _http_client


async def get_async_client() -> httpx.AsyncClient:
    global _http_async_client
    if _http_async_client is None:
        with _async_init_lock:
            if _http_async_client is None:
                _http_async_client = httpx.AsyncClient(
                    timeout=10.0,
                    limits=Limits(max_keepalive_connections=20, max_connections=100)
                )
    return _http_async_client


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        with _supabase_lock:
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
    return _ANON_HEADERS.copy()


def _get_auth_headers(access_token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


async def signup_via_rest_async(email: str, password: str, name: str = None, phone: str = None) -> dict:
    headers = _get_headers()
    user_data = {"email": email, "password": password}
    if name or phone:
        user_data["data"] = {"name": name or "", "phone": phone or ""}
    client = await get_async_client()
    response = await client.post(f"{AUTH_URL}/signup", json=user_data, headers=headers)
    print(f"Signup REST API response: {response.status_code}")
    return response.json()


async def login_via_rest_async(email: str, password: str) -> dict:
    headers = _get_headers()
    client = await get_async_client()
    response = await client.post(
        f"{AUTH_URL}/token?grant_type=password",
        json={"email": email, "password": password},
        headers=headers
    )
    print(f"Login REST API response: {response.status_code}")
    return response.json()


async def logout_via_rest_async(access_token: str) -> dict:
    headers = _get_auth_headers(access_token)
    client = await get_async_client()
    response = await client.post(f"{AUTH_URL}/logout", json={}, headers=headers)
    return response.json() if response.text else {}


async def get_user_via_rest_async(access_token: str) -> dict:
    headers = _get_auth_headers(access_token)
    client = await get_async_client()
    response = await client.get(f"{AUTH_URL}/user", headers=headers)
    if response.status_code == 200:
        return response.json()
    return {}


# ==================== ASYNC DB FUNCTIONS ====================


async def rest_select_async(table: str, filters: dict = None, order: str = None, limit: int = None,
                           offset: int = None, columns: str = "*", like_filters: dict = None) -> list:
    params = [f"select={columns}"]
    if filters:
        for key, value in filters.items():
            if isinstance(value, str) and value.startswith(("eq.", "neq.", "gt.", "gte.", "lt.", "lte.", "in.")):
                params.append(f"{key}={value}")
            else:
                params.append(f"{key}=eq.{value}")
    if like_filters:
        for key, value in like_filters.items():
            params.append(f"{key}=ilike.*{value}*")
    if order:
        params.append(f"order={order}")
    if limit:
        params.append(f"limit={limit}")
    if offset:
        params.append(f"offset={offset}")

    query_string = "&".join(params)
    url = f"{REST_URL}/{table}?{query_string}"

    try:
        client = await get_async_client()
        response = await client.get(url, headers=_get_headers())
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"REST select async error ({table}): {e}")
    return []


async def rest_select_auth_async(table: str, access_token: str, filters: dict = None, order: str = None,
                                 limit: int = None, offset: int = None, columns: str = "*",
                                 like_filters: dict = None) -> list:
    params = [f"select={columns}"]
    if filters:
        for key, value in filters.items():
            if isinstance(value, str) and value.startswith(("eq.", "neq.", "gt.", "gte.", "lt.", "lte.", "in.")):
                params.append(f"{key}={value}")
            else:
                params.append(f"{key}=eq.{value}")
    if like_filters:
        for key, value in like_filters.items():
            params.append(f"{key}=ilike.*{value}*")
    if order:
        params.append(f"order={order}")
    if limit:
        params.append(f"limit={limit}")
    if offset:
        params.append(f"offset={offset}")

    query_string = "&".join(params)
    url = f"{REST_URL}/{table}?{query_string}"

    try:
        client = await get_async_client()
        response = await client.get(url, headers=_get_auth_headers(access_token))
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"REST select auth async error ({table}): {e}")
    return []


async def rest_insert_async(table: str, data: dict) -> dict:
    url = f"{REST_URL}/{table}"
    try:
        client = await get_async_client()
        response = await client.post(url, json=data, headers=_get_headers())
        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST insert async error ({table}): {e}")
    return {}


async def rest_insert_auth_async(table: str, access_token: str, data: dict) -> dict:
    url = f"{REST_URL}/{table}"
    try:
        client = await get_async_client()
        response = await client.post(url, json=data, headers=_get_auth_headers(access_token))
        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
        else:
            print(f"REST insert auth async error ({table}): status={response.status_code}, response={response.text}")
    except Exception as e:
        print(f"REST insert auth async error ({table}): {e}")
    return {}


async def rest_update_async(table: str, data: dict, filters: dict) -> dict:
    filter_parts = []
    for key, value in filters.items():
        if isinstance(value, str) and value.startswith(("eq.", "neq.", "gt.", "gte.", "lt.", "lte.", "in.")):
            filter_parts.append(f"{key}={value}")
        else:
            filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"

    try:
        client = await get_async_client()
        response = await client.patch(url, json=data, headers=_get_headers())
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST update async error ({table}): {e}")
    return {}


async def rest_update_auth_async(table: str, access_token: str, data: dict, filters: dict) -> dict:
    filter_parts = []
    for key, value in filters.items():
        if isinstance(value, str) and value.startswith(("eq.", "neq.", "gt.", "gte.", "lt.", "lte.", "in.")):
            filter_parts.append(f"{key}={value}")
        else:
            filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"

    try:
        client = await get_async_client()
        response = await client.patch(url, json=data, headers=_get_auth_headers(access_token))
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST update auth async error ({table}): {e}")
    return {}


async def rest_delete_async(table: str, filters: dict) -> bool:
    filter_parts = []
    for key, value in filters.items():
        filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"

    try:
        client = await get_async_client()
        response = await client.delete(url, headers=_get_headers())
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"REST delete async error ({table}): {e}")
    return False


async def rest_count_async(table: str, filters: dict = None) -> int:
    params = ["select=count"]
    if filters:
        for key, value in filters.items():
            if isinstance(value, str) and value.startswith(("eq.", "neq.", "gt.", "gte.", "lt.", "lte.")):
                params.append(f"{key}={value}")
            else:
                params.append(f"{key}=eq.{value}")

    query_string = "&".join(params)
    url = f"{REST_URL}/{table}?{query_string}"

    try:
        client = await get_async_client()
        response = await client.get(url, headers=_get_headers())
        if response.status_code == 200:
            result = response.json()
            if result and isinstance(result, list) and len(result) > 0:
                count_val = result[0].get("count")
                if count_val is not None:
                    return int(count_val)
    except Exception as e:
        print(f"REST count async error ({table}): {e}")
    return 0


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


async def upload_image_async(file_data: bytes, file_name: str, bucket: str = "listing-images", access_token: str = None) -> Optional[str]:
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
        client = await get_async_client()
        response = await client.post(
            f"{STORAGE_URL}/object/{bucket}/{storage_path}",
            content=file_data,
            headers=headers,
            timeout=30.0
        )
        if response.status_code in [200, 201]:
            return f"{STORAGE_URL}/object/public/{bucket}/{storage_path}"
    except Exception as e:
        print(f"Image upload async error: {e}")

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
