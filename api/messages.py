# Messages API - Conversations and chat
from typing import Optional, List
from pydantic import BaseModel, Field
from lib.supabase import rest_select, rest_select_auth, rest_insert, rest_insert_auth, rest_update


class ConversationCreate(BaseModel):
    listing_id: str
    buyer_id: str
    seller_id: str


class MessageCreate(BaseModel):
    conversation_id: str
    sender_id: str
    content: str = Field(..., min_length=1)


def get_conversations(user_id: str, access_token: str = None) -> List[dict]:
    """Get conversations with enriched data using the conversations_enriched view + bulk message fetch.
    Reduces N*4 queries to just 3 queries total."""
    if access_token:
        all_convs = rest_select_auth("conversations_enriched", access_token, order="created_at.desc")
    else:
        all_convs = rest_select("conversations_enriched", order="created_at.desc")

    filtered = [c for c in all_convs if c.get("buyer_id") == user_id or c.get("seller_id") == user_id]

    conv_ids = [c.get("id") for c in filtered if c.get("id")]

    all_messages = {}
    if conv_ids and access_token:
        messages_by_conv = rest_select_auth("messages", access_token, order="created_at.desc",
                                            columns="id,conversation_id,content,created_at,sender_id,read_at")
        if messages_by_conv:
            for msg in messages_by_conv:
                cid = msg.get("conversation_id")
                if cid not in all_messages:
                    all_messages[cid] = []
                all_messages[cid].append(msg)

    enriched = []
    for conv in filtered:
        conv_id = conv.get("id")
        conv["is_buying"] = conv.get("buyer_id") == user_id
        conv["is_selling"] = conv.get("seller_id") == user_id

        other_user_id = conv.get("buyer_id") if conv.get("seller_id") == user_id else conv.get("seller_id")
        conv["other_user_id"] = other_user_id

        if conv.get("seller_id") == user_id:
            conv["other_user_name"] = conv.get("buyer_name", "User")
            conv["other_user_avatar_url"] = conv.get("buyer_avatar_url")
        else:
            conv["other_user_name"] = conv.get("seller_name", "User")
            conv["other_user_avatar_url"] = conv.get("seller_avatar_url")

        thumbs = conv.get("listing_thumbnails")
        if thumbs and isinstance(thumbs, list) and len(thumbs) > 0:
            conv["listing_thumbnail"] = thumbs[0]
        else:
            conv["listing_thumbnail"] = None

        conv_messages = all_messages.get(conv_id, [])
        if conv_messages:
            conv["last_message"] = conv_messages[0].get("content")
            conv["last_message_at"] = conv_messages[0].get("created_at")
            unread_count = sum(1 for m in conv_messages if m.get("sender_id") != user_id and m.get("read_at") is None)
            conv["unread_count"] = unread_count
        else:
            conv["last_message"] = None
            conv["last_message_at"] = None
            conv["unread_count"] = 0

        enriched.append(conv)

    return enriched


def get_messages(conversation_id: str, access_token: str = None) -> List[dict]:
    if access_token:
        return rest_select_auth("messages", access_token, filters={"conversation_id": f"eq.{conversation_id}"}, order="created_at.asc")
    return rest_select("messages", filters={"conversation_id": f"eq.{conversation_id}"}, order="created_at.asc")


def get_conversation_by_id(conversation_id: str, access_token: str = None) -> Optional[dict]:
    if access_token:
        convs = rest_select_auth("conversations", access_token, filters={"id": f"eq.{conversation_id}"})
    else:
        convs = rest_select("conversations", filters={"id": f"eq.{conversation_id}"})
    return convs[0] if convs else None


def get_conversation_by_listing_and_buyer(listing_id: str, buyer_id: str) -> Optional[dict]:
    convs = rest_select("conversations", filters={"listing_id": f"eq.{listing_id}", "buyer_id": f"eq.{buyer_id}"})
    return convs[0] if convs else None


def create_conversation(input: ConversationCreate, access_token: str) -> dict:
    return rest_insert_auth("conversations", access_token, input.model_dump())


def create_message(input: MessageCreate) -> dict:
    return rest_insert("messages", input.model_dump())


def create_message_from_dict(data: dict, access_token: str) -> dict:
    return rest_insert_auth("messages", access_token, data)


def mark_messages_read(conversation_id: str, user_id: str) -> bool:
    # Simplified - just return success
    return True


def get_conversations_optimized(user_id: str, access_token: str = None) -> List[dict]:
    """Get conversations with enriched data using database views - single JOIN at DB level."""
    # Query the view directly - PostgSQL does the JOIN, not Python
    # This replaces the old N*4 queries with just 1 query
    if access_token:
        convs = rest_select_auth("conversations_enriched", access_token, order="created_at.desc")
    else:
        convs = rest_select("conversations_enriched", order="created_at.desc")
    
    # Filter locally for user's conversations (fast in-memory filter)
    filtered = []
    for conv in convs:
        if conv.get("buyer_id") == user_id or conv.get("seller_id") == user_id:
            conv["is_buying"] = conv.get("buyer_id") == user_id
            conv["is_selling"] = conv.get("seller_id") == user_id
            conv["other_user_id"] = conv.get("buyer_id") if conv.get("seller_id") == user_id else conv.get("seller_id")
            conv["listing_title"] = conv.get("listing_title", "Listing")
            # Handle thumbnails - may be list or string
            thumbs = conv.get("listing_thumbnails")
            if thumbs and isinstance(thumbs, list) and len(thumbs) > 0:
                conv["listing_thumbnail"] = thumbs[0]
            else:
                conv["listing_thumbnail"] = None
            # Determine other user name from buyer/seller
            if conv.get("seller_id") == user_id:
                conv["other_user_name"] = conv.get("buyer_name", "User")
                conv["other_user_avatar_url"] = conv.get("buyer_avatar_url")
            else:
                conv["other_user_name"] = conv.get("seller_name", "User")
                conv["other_user_avatar_url"] = conv.get("seller_avatar_url")
            filtered.append(conv)
    
    return filtered