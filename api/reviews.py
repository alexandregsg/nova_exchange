# Reviews API - Seller reviews
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select_async, rest_insert_async


class ReviewInput(BaseModel):
    reviewer_id: str
    seller_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    transaction_id: Optional[str] = None


async def create_review(input: ReviewInput) -> dict:
    if input.reviewer_id == input.seller_id:
        raise ValueError("Cannot review yourself")
    return await rest_insert_async("reviews", input.model_dump())


async def get_reviews_by_seller(seller_id: str) -> List[dict]:
    reviews = await rest_select_async("reviews", filters={"seller_id": f"eq.{seller_id}"}, order="created_at.desc")

    if not reviews:
        return []

    # Batch fetch all reviewer profiles in a single query (fixes N+1)
    reviewer_ids = list({r.get("reviewer_id") for r in reviews if r.get("reviewer_id")})
    if not reviewer_ids:
        return reviews

    profiles = await rest_select_async("profiles", filters={"user_id": f"in.({','.join(reviewer_ids)})"})
    name_map = {p["user_id"]: p.get("name", "Anonymous") for p in profiles}

    for review in reviews:
        review["reviewer_name"] = name_map.get(review.get("reviewer_id"), "Anonymous")

    return reviews


async def get_average_rating(seller_id: str) -> dict:
    reviews = await rest_select_async("reviews", filters={"seller_id": f"eq.{seller_id}"})

    if not reviews:
        return {"average_rating": 0.0, "review_count": 0}

    ratings = [r.get("rating") for r in reviews if r.get("rating")]
    avg = sum(ratings) / len(ratings) if ratings else 0.0

    return {"average_rating": round(avg, 1), "review_count": len(ratings)}


async def get_reviews_with_average(seller_id: str) -> tuple:
    """Fetch reviews and average rating in a single batch (avoids double query)."""
    reviews = await rest_select_async("reviews", filters={"seller_id": f"eq.{seller_id}"}, order="created_at.desc")

    if not reviews:
        return [], {"average_rating": 0.0, "review_count": 0}

    # Batch fetch reviewer profiles (fixes N+1)
    reviewer_ids = list({r.get("reviewer_id") for r in reviews if r.get("reviewer_id")})
    profiles = await rest_select_async("profiles", filters={"user_id": f"in.({','.join(reviewer_ids)})"}) if reviewer_ids else []
    name_map = {p["user_id"]: p.get("name", "Anonymous") for p in profiles}

    for review in reviews:
        review["reviewer_name"] = name_map.get(review.get("reviewer_id"), "Anonymous")

    # Compute average from the same data (no second query)
    ratings = [r.get("rating") for r in reviews if r.get("rating")]
    avg = sum(ratings) / len(ratings) if ratings else 0.0
    rating_info = {"average_rating": round(avg, 1), "review_count": len(ratings)}

    return reviews, rating_info
