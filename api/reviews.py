# Reviews API - Seller reviews
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select, rest_insert


class ReviewInput(BaseModel):
    reviewer_id: str
    seller_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


def create_review(input: ReviewInput) -> dict:
    if input.reviewer_id == input.seller_id:
        raise ValueError("Cannot review yourself")
    return rest_insert("reviews", input.model_dump())


def get_reviews_by_seller(seller_id: str) -> List[dict]:
    reviews = rest_select("reviews", filters={"seller_id": f"eq.{seller_id}"}, order="created_at.desc")
    
    enriched = []
    for review in reviews:
        # Get reviewer name from profiles
        profiles = rest_select("profiles", filters={"user_id": f"eq.{review.get('reviewer_id')}"})
        if profiles:
            review["reviewer_name"] = profiles[0].get("name")
        enriched.append(review)
    
    return enriched


def get_average_rating(seller_id: str) -> dict:
    reviews = rest_select("reviews", filters={"seller_id": f"eq.{seller_id}"})
    
    if not reviews:
        return {"average_rating": 0.0, "review_count": 0}
    
    ratings = [r.get("rating") for r in reviews if r.get("rating")]
    avg = sum(ratings) / len(ratings) if ratings else 0.0
    
    return {"average_rating": round(avg, 1), "review_count": len(ratings)}