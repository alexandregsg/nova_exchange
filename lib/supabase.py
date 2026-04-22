# Supabase client configuration
import os
import httpx
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

AUTH_URL = f"{SUPABASE_URL}/auth/v1"
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"


def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Supabase URL and anon key must be set")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


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


# REST API Auth functions using httpx
def signup_via_rest(email: str, password: str) -> dict:
    """Sign up using REST API directly"""
    headers = _get_headers()
    response = httpx.post(
        f"{AUTH_URL}/signup",
        json={"email": email, "password": password},
        headers=headers,
        timeout=10.0
    )
    print(f"Signup REST API response: {response.status_code} - {response.text}")
    return response.json()


def login_via_rest(email: str, password: str) -> dict:
    """Login using REST API directly"""
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
    """Logout using REST API directly"""
    headers = _get_auth_headers(access_token)
    response = httpx.post(
        f"{AUTH_URL}/logout",
        json={},
        headers=headers,
        timeout=10.0
    )
    return response.json() if response.text else {}


def get_user_via_rest(access_token: str) -> dict:
    """Get current user using REST API"""
    headers = _get_auth_headers(access_token)
    response = httpx.get(f"{AUTH_URL}/user", headers=headers, timeout=5.0)
    if response.status_code == 200:
        return response.json()
    return {}


def rest_select_auth(table: str, access_token: str, filters: dict = None, order: str = None, limit: int = None) -> list:
    """Select rows using user's access token (authenticated)"""
    params = []
    if filters:
        for key, value in filters.items():
            # Check if value already starts with "eq." - don't add prefix again
            if isinstance(value, str) and value.startswith("eq."):
                params.append(f"{key}={value}")
            else:
                params.append(f"{key}=eq.{value}")
    if order:
        params.append(f"order={order}")
    if limit:
        params.append(f"limit={limit}")
    
    query_string = "&".join(params) if params else ""
    url = f"{REST_URL}/{table}" + (f"?{query_string}" if query_string else "")
    
    # Use authenticated headers
    auth_headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = httpx.get(url, headers=auth_headers, timeout=10.0)
        print(f"DEBUG rest_select_auth: status = {response.status_code}, url = {url}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"REST select auth error ({table}): {e}")
    return []


def rest_update_auth(table: str, access_token: str, data: dict, filters: dict) -> dict:
    """Update rows using user's access token (authenticated)"""
    filter_parts = []
    for key, value in filters.items():
        if isinstance(value, str) and value.startswith("eq."):
            filter_parts.append(f"{key}={value}")
        else:
            filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"
    
    auth_headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = httpx.patch(url, json=data, headers=auth_headers, timeout=10.0)
        print(f"DEBUG rest_update_auth: status = {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST update auth error ({table}): {e}")
    return {}


# Database REST API functions
def rest_select(table: str, filters: dict = None, order: str = None, limit: int = None) -> list:
    """Select rows from table using REST API"""
    params = []
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
    
    query_string = "&".join(params) if params else ""
    url = f"{REST_URL}/{table}" + (f"?{query_string}" if query_string else "")
    
    try:
        response = httpx.get(url, headers=_get_headers(), timeout=10.0)
        print(f"DEBUG rest_select: status={response.status_code}, url={url}")
        if response.status_code == 200:
            result = response.json()
            print(f"DEBUG rest_select result for {table}: {result}")
            return result
    except Exception as e:
        print(f"REST select error ({table}): {e}")
    return []


def rest_insert(table: str, data: dict) -> dict:
    """Insert row into table using REST API"""
    url = f"{REST_URL}/{table}"
    print(f"DEBUG rest_insert: url = {url}, data = {data}")
    try:
        response = httpx.post(url, json=data, headers=_get_headers(), timeout=10.0)
        print(f"DEBUG rest_insert: status = {response.status_code}, response = {response.text}")
        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST insert error ({table}): {e}")
    return {}


def rest_insert_auth(table: str, access_token: str, data: dict) -> dict:
    """Insert row into table using authenticated user's access token"""
    url = f"{REST_URL}/{table}"
    auth_headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    print(f"DEBUG rest_insert_auth: url = {url}, data = {data}")
    try:
        response = httpx.post(url, json=data, headers=auth_headers, timeout=10.0)
        print(f"DEBUG rest_insert_auth: status = {response.status_code}, response = {response.text}")
        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST insert auth error ({table}): {e}")
    return {}


def rest_update(table: str, data: dict, filters: dict) -> dict:
    """Update row in table using REST API"""
    # Build filter string - assume filters already have eq. prefix if needed
    filter_parts = []
    for key, value in filters.items():
        # If value already starts with eq., use as-is, otherwise add eq. prefix
        if isinstance(value, str) and value.startswith("eq."):
            filter_parts.append(f"{key}={value}")
        else:
            filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"
    print(f"DEBUG rest_update: url = {url}, data = {data}")
    
    try:
        # Increased timeout to 30 seconds for array updates
        response = httpx.patch(url, json=data, headers=_get_headers(), timeout=30.0)
        print(f"DEBUG rest_update: status = {response.status_code}, response = {response.text[:200] if response.text else 'empty'}")
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0]
            return result
    except Exception as e:
        print(f"REST update error ({table}): {e}")
    return {}


def rest_delete(table: str, filters: dict) -> bool:
    """Delete row from table using REST API"""
    filter_parts = []
    for key, value in filters.items():
        filter_parts.append(f"{key}=eq.{value}")
    filter_string = "&".join(filter_parts)
    url = f"{REST_URL}/{table}?{filter_string}"
    
    try:
        response = httpx.delete(url, headers=_get_headers(), timeout=10.0)
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


def upload_image(file_data: bytes, file_name: str, bucket: str = "listing-images") -> Optional[str]:
    """Upload image to Supabase Storage and return public URL"""
    import uuid
    
    file_ext = file_name.split('.')[-1].lower() if '.' in file_name else 'jpg'
    # Fix: map jpg to jpeg for proper MIME type
    if file_ext == 'jpg':
        file_ext = 'jpeg'
    
    storage_path = f"{uuid.uuid4()}.{file_ext}"
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
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
        print(f"DEBUG upload: status={response.status_code}, bucket={bucket}, path={storage_path}")
        print(f"DEBUG upload response: {response.text[:500] if response.text else 'empty'}")
        if response.status_code in [200, 201]:
            return f"{STORAGE_URL}/object/public/{bucket}/{storage_path}"
    except Exception as e:
        print(f"Image upload error: {e}")
    
    return None