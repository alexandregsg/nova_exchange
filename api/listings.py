# Listings API - CRUD operations for marketplace listings
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select_async, rest_insert_async, rest_update_async, rest_delete_async, invalidate_cache
from lib.cache import cache_get, cache_set


class ListingInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    condition: str
    category: str
    location: Optional[str] = None
    image_urls: List[str] = []
    user_id: str
    seller_email: str


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    condition: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    image_urls: Optional[List[str]] = Field(default=None)


async def create_listing(input: ListingInput) -> dict:
    data = {
        "user_id": input.user_id,
        "title": input.title,
        "description": input.description,
        "price": input.price,
        "condition": input.condition,
        "category": input.category,
        "location": input.location,
        "image_urls": input.image_urls,
        "seller_email": input.seller_email,
        "status": "active"
    }
    result = await rest_insert_async("listings", data)
    invalidate_cache("featured")
    return result


async def get_listings(limit: int = 20, offset: int = 0) -> tuple[List[dict], int]:
    results = await rest_select_async("listings", order="created_at.desc", limit=limit)
    return results, len(results)


async def get_listing_by_id(id: str, access_token: str = None) -> Optional[dict]:
    results = await rest_select_async("listings", filters={"id": f"eq.{id}"})
    return results[0] if results else None


async def get_listing_with_seller(id: str, access_token: str = None) -> Optional[dict]:
    results = await rest_select_async("listings", filters={"id": f"eq.{id}"},
                         columns="*,profiles!listings_user_id_fkey(name,phone,show_phone,avatar_url,created_at)")
    if results:
        return results[0]
    return await get_listing_by_id(id)


async def get_listing_public(id: str) -> Optional[dict]:
    results = await rest_select_async("listings_public", filters={"id": f"eq.{id}"})
    return results[0] if results else None


async def get_listings_by_user(user_id: str) -> List[dict]:
    return await rest_select_async("listings", filters={"user_id": f"eq.{user_id}"}, order="created_at.desc")


async def update_listing(id: str, input_data: dict, user_id: str) -> Optional[dict]:
    if isinstance(input_data, ListingUpdate):
        update_data = {k: v for k, v in input_data.model_dump().items() if v is not None}
    else:
        update_data = {k: v for k, v in input_data.items() if v is not None}
    if not update_data:
        return None
    result = await rest_update_async("listings", update_data, {"id": f"eq.{id}", "user_id": f"eq.{user_id}"})
    invalidate_cache("featured")
    return result


async def delete_listing(id: str, user_id: str) -> bool:
    result = await rest_delete_async("listings", {"id": f"eq.{id}", "user_id": f"eq.{user_id}"})
    invalidate_cache("featured")
    return result


async def get_featured_listings(limit: int = 6) -> List[dict]:
    cache_key = f"featured_listings:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached[:limit] if len(cached) > limit else cached
    # Push status filter to database instead of client-side filtering
    results = await rest_select_async("listings", filters={"status": "neq.sold"}, order="created_at.desc", limit=limit,
                          columns="id,title,price,condition,category,image_urls,status,user_id,seller_email")
    cache_set(cache_key, results, ttl=30)
    return results


async def search_listings(query: str = "", category: Optional[str] = None, condition: Optional[str] = None,
                   sort: str = "created_desc", min_price: float = None, max_price: float = None,
                   limit: int = 20, offset: int = 0) -> tuple[List[dict], int]:
    filters = {"status": "neq.sold"}  # Push status filter to database
    if category:
        filters["category"] = f"eq.{category}"
    if condition:
        filters["condition"] = f"eq.{condition}"
    if min_price is not None:
        filters["price"] = f"gte.{min_price}"
    if max_price is not None:
        filters["price_max"] = f"lte.{max_price}"

    like_filters = {}
    if query:
        like_filters["title"] = query

    order_map = {
        "created_asc": "created_at.asc",
        "created_desc": "created_at.desc",
        "price_asc": "price.asc",
        "price_desc": "price.desc"
    }
    order = order_map.get(sort, "created_at.desc")

    results = await rest_select_async("listings", filters=filters, order=order,
                          columns="id,title,price,condition,category,image_urls,status,user_id,seller_email,created_at",
                          like_filters=like_filters if like_filters else None)

    # Client-side max_price filter as fallback (in case DB filter didn't apply due to column name)
    if max_price is not None:
        results = [r for r in results if r.get("price", 0) <= max_price]

    total_count = len(results)
    results = results[offset:offset + limit]

    return results, total_count
