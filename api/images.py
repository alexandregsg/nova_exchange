# Images API - Image upload/delete to Supabase Storage
from typing import Optional
from supabase import Client
from lib.constants import MAX_FILE_SIZE, ALLOWED_TYPES


def validate_image(file_data: bytes, filename: str) -> tuple[bool, Optional[str]]:
    if len(file_data) > MAX_FILE_SIZE:
        return False, f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
    
    content_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_extensions = [t.split("/")[1] for t in ALLOWED_TYPES]
    
    if content_type not in allowed_extensions:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


async def upload_image(file_data: bytes, filename: str, user_id: str) -> dict:
    import uuid
    from lib.supabase import get_db
    db = get_db()
    
    valid, error = validate_image(file_data, filename)
    if not valid:
        raise ValueError(error)
    
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    new_filename = f"{user_id}/{uuid.uuid4()}.{ext}"
    
    response = db.storage.from_("listing-images").upload(new_filename, file_data)
    
    if response.path:
        public_url = db.storage.from_("listing-images").get_public_url(response.path)
        return {"url": public_url, "path": response.path}
    
    raise ValueError("Upload failed")


async def delete_image(url: str) -> bool:
    from lib.supabase import get_db
    db = get_db()
    
    path = url.split("/storage/")[1].split("/")[-1] if "/storage/" in url else url
    
    response = db.storage.from_("listing-images").remove([path])
    return len(response) > 0


def get_public_url(path: str) -> str:
    from lib.supabase import get_db
    db = get_db()
    return db.storage.from_("listing-images").get_public_url(path)