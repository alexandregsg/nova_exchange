# Listings API - CRUD operations for marketplace listings
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select, rest_insert, rest_update, rest_delete


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


def create_listing(input: ListingInput) -> dict:
    data = {
        "user_id": input.user_id,
        "title": input.title,
        "description": input.description,
        "price": input.price,
        "condition": input.condition,
        "category": input.category,
        "location": input.location,
        "image_urls": input.image_urls,
        "seller_email": input.seller_email
    }
    return rest_insert("listings", data)


def get_listings(limit: int = 20, offset: int = 0) -> tuple[List[dict], int]:
    results = rest_select("listings", order="created_at.desc", limit=limit)
    return results, len(results)


def get_listing_by_id(id: str) -> Optional[dict]:
    results = rest_select("listings", filters={"id": f"eq.{id}"})
    return results[0] if results else None


def get_listings_by_user(user_id: str) -> List[dict]:
    return rest_select("listings", filters={"user_id": f"eq.{user_id}"}, order="created_at.desc")


def update_listing(id: str, input_data: dict, user_id: str) -> Optional[dict]:
    if isinstance(input_data, ListingUpdate):
        update_data = {k: v for k, v in input_data.model_dump().items() if v is not None}
    else:
        update_data = {k: v for k, v in input_data.items() if v is not None}
    if not update_data:
        return None
    return rest_update("listings", update_data, {"id": f"eq.{id}", "user_id": f"eq.{user_id}"})


def delete_listing(id: str, user_id: str) -> bool:
    return rest_delete("listings", {"id": f"eq.{id}", "user_id": f"eq.{user_id}"})


def get_featured_listings(limit: int = 6) -> List[dict]:
    return rest_select("listings", order="created_at.desc", limit=limit)


def search_listings(query: str = "", category: Optional[str] = None, condition: Optional[str] = None, 
                   sort: str = "created_desc", min_price: float = None, max_price: float = None) -> List[dict]:
    # REST API doesn't support full-text search well, so we filter after fetching
    results = rest_select("listings", order="created_at.desc")
    
    filtered = []
    for item in results:
        # Only show active listings
        if item.get("status") == "sold":
            continue
        if query:
            q = query.lower()
            title = item.get("title", "").lower()
            desc = item.get("description", "").lower()
            if q not in title and q not in desc:
                continue
        if category and item.get("category") != category:
            continue
        if condition and item.get("condition") != condition:
            continue
        # Price filtering
        price = item.get("price", 0)
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        filtered.append(item)
    
    # Sort results
    if sort == "created_asc":
        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=False)
    elif sort == "price_asc":
        filtered.sort(key=lambda x: x.get("price", 0), reverse=False)
    elif sort == "price_desc":
        filtered.sort(key=lambda x: x.get("price", 0), reverse=True)
    else:  # created_desc (default) - already sorted by REST API, but ensure
        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return filtered