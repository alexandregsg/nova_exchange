# Nova-Exchange FastAPI Application
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from typing import List
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime

from lib.supabase import init_supabase, get_db, is_allowed_email_domain

from fastapi.middleware.gzip import GZipMiddleware

# Create FastAPI app
app = FastAPI(
    title="Nova Exchange",
    description="Nova SBE Marketplace for Students",
    version="1.0.0"
)

# Initialize Supabase
init_supabase()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
from jinja2 import Environment, FileSystemLoader, select_autoescape
jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)
templates = Jinja2Templates(env=jinja_env)

# GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for reliability (Criteria 1)
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch all unhandled exceptions - prevents crashes"""
    import logging
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return templates.TemplateResponse(request, "error.html", {
        "request": request,
        "user": None,
        "title": "Something went wrong",
        "message": "We encountered an unexpected error. Please try again.",
        "icon": "&#128533;",
        "now_year": datetime.now().year,
    }, status_code=500)

@app.get("/error/{code}")
async def error_page(request: Request, code: int):
    """Custom error pages"""
    user = await get_current_user(request)
    errors = {
        404: ("Page Not Found", "The page you're looking for doesn't exist.", "&#128269;"),
        403: ("Access Denied", "You don't have permission to view this page.", "&#128683;"),
        500: ("Server Error", "Something went wrong on our end.", "&#128533;"),
    }
    title, message, icon = errors.get(code, ("Error", "An error occurred.", "&#9888;&#65039;"))
    return templates.TemplateResponse(request, "error.html", {
        "request": request,
        "user": user,
        "title": title,
        "message": message,
        "icon": icon,
        "now_year": datetime.now().year,
    }, status_code=code)

# Import API functions
from api.listings import get_featured_listings, search_listings, get_listing_by_id, get_listing_public, get_listings_by_user, create_listing as create_listing_func, ListingInput
from api.profiles import get_profile_by_user_id, ensure_profile
from api.messages import get_conversations, get_messages, get_conversation_by_id
from api.reviews import get_reviews_with_average
from lib.auth import get_current_user
from lib.supabase import rest_select_async, rest_select_auth_async, rest_count_async, rest_insert_auth_async, rest_update_auth_async, rest_insert_async, upload_image_async
from lib.cache import cache_get, cache_set


# ==================== ROUTES ====================

@app.get("/")
async def home(request: Request):
    try:
        featured = await get_featured_listings(6)
    except Exception as e:
        print(f"Error: {e}")
        featured = []

    cached_count = cache_get("total_active_listings")
    if cached_count is not None:
        total_active = cached_count
    else:
        total_active = await rest_count_async("listings", {"status": "neq.sold"})
        cache_set("total_active_listings", total_active, ttl=60)
    
    user = await get_current_user(request)
    return templates.TemplateResponse(request, "home.html", {
        "request": request,
        "user": user,
        "featured": featured,
        "total_active": total_active,
        "now_year": datetime.now().year,
    })


@app.get("/browse")
async def browse(request: Request, q: str = "", category: str = "", condition: str = "",
             sort: str = "created_desc", min_price: Optional[str] = None, max_price: Optional[str] = None,
             page: int = 1):
    try:
        min_p = float(min_price) if min_price and min_price.strip() else None
        max_p = float(max_price) if max_price and max_price.strip() else None
        limit = 20
        offset = (page - 1) * limit
        results, total_count = await search_listings(q, category or None, condition or None, sort, min_p, max_p, limit=limit, offset=offset)
    except Exception:
        results = []
        total_count = 0

    count = len(results)
    total_pages = max(1, (total_count + limit - 1) // limit)
    page_info = f"Showing {offset + 1}-{offset + count} of {total_count} results" if total_count > 0 else "No results"
    
    user = await get_current_user(request)
    return templates.TemplateResponse(request, "browse.html", {
        "request": request,
        "user": user,
        "results": results,
        "q": q,
        "category": category,
        "condition": condition,
        "sort": sort,
        "min_price": min_price,
        "max_price": max_price,
        "page": page,
        "total_pages": total_pages,
        "page_info": page_info,
        "now_year": datetime.now().year,
    })


@app.get("/listings/new")
async def create_listing_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    return templates.TemplateResponse(request, "listings/new.html", {
        "request": request,
        "user": user,
        "now_year": datetime.now().year,
    })


@app.post("/api/listings")
async def create_listing(request: Request,
    title: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    condition: str = Form(...),
    category: str = Form(""),
    location: str = Form(""),
    image_1: UploadFile = File(None),
    image_2: UploadFile = File(None),
    image_3: UploadFile = File(None)
):
    access_token = request.cookies.get("sb-access-token", "")
    
    if not access_token:
        return RedirectResponse("/auth/login")
    
    from lib.supabase import get_user_via_rest_async
    user_data = await get_user_via_rest_async(access_token)
    
    if not user_data:
        return RedirectResponse("/auth/login")
    
    user_id = user_data.get("id", "")
    user_email = user_data.get("email", "")
    
    if not user_id:
        return RedirectResponse("/auth/login")
    
    image_urls = []
    image_files = [image_1, image_2, image_3]
    
    for idx, img in enumerate(image_files):
        if img and len(image_urls) < 3:
            try:
                contents = await img.read()
                if contents:
                    file_name = img.filename or "image.jpg"
                    image_url = await upload_image_async(contents, file_name)
                    if image_url:
                        image_urls.append(image_url)
            except Exception as e:
                print(f"Image upload error: {e}")
    
    if location and location.strip().isdigit():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html><body class="max-w-xl mx-auto px-4 py-8">
            <h1 class="text-2xl font-bold text-red-600 mb-4">Invalid Location</h1>
            <p class="text-gray-700 mb-4">Location cannot be a number only. Please enter a valid location name (e.g., Campus, Residence Hall).</p>
            <a href="javascript:history.back()" class="inline-block bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700">Go Back</a>
        </body></html>
        """, status_code=400)

    listing_input = ListingInput(
        title=title,
        description=description or None,
        price=price,
        condition=condition,
        category=category or "Other",
        location=location or None,
        image_urls=image_urls,
        user_id=user_id,
        seller_email=user_email
    )
    listing = await create_listing_func(listing_input)
    
    if listing and listing.get('id'):
        lid = listing.get('id', '')
        return RedirectResponse(f"/listings/{lid}", status_code=303)
    else:
        # Listing creation might have failed
        return RedirectResponse("/browse", status_code=303)


@app.get("/listings/{listing_id}")
async def listing_detail(request: Request, listing_id: str):
    listing = await get_listing_public(listing_id)
    if not listing:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": None,
            "title": "Listing not found",
            "message": "The listing you're looking for doesn't exist.",
            "icon": "&#128269;",
            "now_year": datetime.now().year,
        }, status_code=404)

    created_at_raw = listing.get('created_at', '')
    posted_date_formatted = ''
    if created_at_raw:
        try:
            dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
            posted_date_formatted = dt.strftime('%d %b %Y at %H:%M')
        except (ValueError, TypeError):
            posted_date_formatted = created_at_raw[:10]

    seller_id = listing.get('user_id', '')
    listing_status = listing.get('status', 'active')
    is_sold = listing_status == 'sold'

    # Fetch seller phone data from profiles using authenticated request
    access_token = request.cookies.get("sb-access-token", "")
    if seller_id and access_token:
        try:
            profile_data = await rest_select_auth_async("profiles", access_token, filters={"user_id": f"eq.{seller_id}"}, columns="phone,show_phone")
            if profile_data:
                listing['seller_phone'] = profile_data[0].get('phone')
                listing['seller_show_phone'] = profile_data[0].get('show_phone', False)
        except Exception as e:
            print(f"Error fetching seller phone: {e}")

    user = await get_current_user(request)
    current_user_id = user.get('id', '') if user else ''
    is_seller = current_user_id and current_user_id == seller_id

    import json
    image_urls_raw = listing.get('image_urls')
    image_urls = []
    if image_urls_raw:
        if isinstance(image_urls_raw, list):
            image_urls = image_urls_raw
        elif isinstance(image_urls_raw, str):
            try:
                image_urls = json.loads(image_urls_raw)
            except (json.JSONDecodeError, ValueError):
                if image_urls_raw.startswith('{') and image_urls_raw.endswith('}'):
                    image_urls = [u.strip().strip('"') for u in image_urls_raw[1:-1].split(',') if u.strip()]
                else:
                    image_urls = [image_urls_raw]

    # Generate status badge
    status_colors = {"active": "bg-green-100 text-green-800", "sold": "bg-gray-100 text-gray-800", "pending": "bg-yellow-100 text-yellow-800"}
    status_class = status_colors.get(listing_status, "bg-gray-100 text-gray-800")
    status_badge = f'<span class="{status_class} px-3 py-1 rounded">{listing_status.capitalize()}</span>'

    # Generate action buttons
    edit_button = ""
    contact_button = ""
    show_number_button = ""
    mark_sold_button = ""

    # Show number button for both seller and buyer when phone is public
    if listing.get('seller_show_phone'):
        show_number_button = f'''
            <button type="button" id="reveal-phone-btn" onclick="revealPhoneNumber()" class="mt-3 inline-block w-full border border-emerald-600 text-emerald-600 px-6 py-3 rounded-lg text-center hover:bg-emerald-50">
                <span id="phone-btn-text">Show Number</span>
                <span id="phone-btn-number" style="display:none"></span>
            </button>
        '''

    if is_seller:
        edit_button = f'<a href="/listings/{listing_id}/edit" class="mt-4 inline-block w-full bg-gray-600 text-white px-6 py-3 rounded-lg text-center hover:bg-gray-700">Edit Listing</a>'
        if not is_sold:
            mark_sold_button = f'<button type="button" onclick="openMarkSoldModal()" class="mt-3 inline-block w-full bg-emerald-600 text-white px-6 py-3 rounded-lg text-center hover:bg-emerald-700 font-medium">Mark as Sold</button>'
    else:
        contact_button = f'<a href="/messages/new?listing_id={listing_id}" class="mt-4 inline-block w-full bg-emerald-600 text-white px-6 py-3 rounded-lg text-center hover:bg-emerald-700">Contact Seller</a>'

    return templates.TemplateResponse(request, "listings/detail.html", {
        "request": request,
        "user": user,
        "listing": listing,
        "listing_id": listing_id,
        "title": listing.get('title', 'Untitled'),
        "price": listing.get('price', 0),
        "description": listing.get('description', 'No description'),
        "condition": listing.get('condition', 'N/A'),
        "category": listing.get('category', 'Other'),
        "location": listing.get('location', ''),
        "seller_email": listing.get('seller_email', ''),
        "seller_id": seller_id,
        "seller_name": listing.get('seller_name') or listing.get('seller_email', ''),
        "seller_avatar_url": listing.get('seller_avatar_url'),
        "seller_join_date": listing.get('created_at', 'Recently')[:10] if listing.get('created_at') else 'Recently',
        "seller_phone": listing.get('seller_phone'),
        "seller_show_phone": listing.get('seller_show_phone', False),
        "posted_date_formatted": posted_date_formatted,
        "is_seller": is_seller,
        "is_sold": is_sold,
        "image_urls": image_urls,
        "status_badge": status_badge,
        "edit_button": edit_button,
        "contact_button": contact_button,
        "show_number_button": show_number_button,
        "mark_sold_button": mark_sold_button,
        "now_year": datetime.now().year,
    })


@app.get("/listings/{listing_id}/edit")
async def edit_listing_page(request: Request, listing_id: str):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    listing = await get_listing_by_id(listing_id)
    if not listing:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": user,
            "title": "Listing not found",
            "message": "The listing you're looking for doesn't exist.",
            "icon": "&#128269;",
            "now_year": datetime.now().year,
        }, status_code=404)
    
    current_user_id = user.get('id', '')
    seller_id = listing.get('user_id', '')
    
    if current_user_id != seller_id:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": user,
            "title": "Access Denied",
            "message": "You don't have permission to edit this listing.",
            "icon": "&#128683;",
            "now_year": datetime.now().year,
        }, status_code=403)

    import json
    image_urls = listing.get('image_urls', []) or []
    if image_urls and isinstance(image_urls, str):
        try:
            image_urls = json.loads(image_urls)
        except (json.JSONDecodeError, ValueError):
            image_urls = [image_urls]

    return templates.TemplateResponse(request, "listings/edit.html", {
        "request": request,
        "user": user,
        "listing": listing,
        "listing_id": listing_id,
        "title": listing.get('title', ''),
        "description": listing.get('description', '') or '',
        "price": listing.get('price', 0),
        "condition": listing.get('condition', ''),
        "category": listing.get('category', ''),
        "location": listing.get('location', '') or '',
        "image_urls": image_urls,
        "supabase_url": os.getenv('NEXT_PUBLIC_SUPABASE_URL', ''),
        "supabase_anon_key": os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY', ''),
        "now_year": datetime.now().year,
    })


@app.post("/api/listings/{listing_id}/edit")
async def edit_listing_submit(request: Request, listing_id: str,
    title: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    condition: str = Form(...),
    category: str = Form(""),
    location: str = Form(""),
    existing_images: str = Form(""),
    new_images_data: str = Form(""),
    new_image_1: UploadFile = File(None),
    new_image_2: UploadFile = File(None),
    new_image_3: UploadFile = File(None)
):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    listing = await get_listing_by_id(listing_id)
    if not listing:
        return HTMLResponse("Listing not found", status_code=404)
    
    current_user_id = user.get('id', '')
    seller_id = listing.get('user_id', '')
    
    if current_user_id != seller_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    import base64
    import json
    
    image_urls = []
    if existing_images:
        image_urls = [url.strip() for url in existing_images.split(',') if url.strip()]
    
    if new_images_data:
        try:
            new_image_list = json.loads(new_images_data)
            for idx, base64_data in enumerate(new_image_list):
                if len(image_urls) >= 3:
                    break
                try:
                    header, data = base64_data.split(',', 1)
                    contents = base64.b64decode(data)
                    file_name = f"edit_image_{idx}.jpg"
                    image_url = await upload_image_async(contents, file_name)
                    if image_url:
                        image_urls.append(image_url)
                except Exception as e:
                    print(f"Error processing base64 image: {e}")
        except Exception as e:
            print(f"Error parsing new_images_data: {e}")
    
    new_files = [new_image_1, new_image_2, new_image_3]
    
    for idx, new_image in enumerate(new_files):
        if new_image and len(image_urls) < 3:
            try:
                contents = await new_image.read()
                file_name = new_image.filename or "image.jpg"
                
                image_url = await upload_image_async(contents, file_name)
                
                if image_url:
                    image_urls.append(image_url)
            except Exception as e:
                print(f"Image upload error: {e}")
    
    if location and location.strip().isdigit():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html><body class="max-w-xl mx-auto px-4 py-8">
            <h1 class="text-2xl font-bold text-red-600 mb-4">Invalid Location</h1>
            <p class="text-gray-700 mb-4">Location cannot be a number only. Please enter a valid location name (e.g., Campus, Residence Hall).</p>
            <a href="javascript:history.back()" class="inline-block bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700">Go Back</a>
        </body></html>
        """, status_code=400)

    update_data = {
        "title": title,
        "description": description or None,
        "price": price,
        "condition": condition,
        "category": category,
        "location": location or None,
        "image_urls": image_urls
    }
    
    from api.listings import update_listing
    await update_listing(listing_id, update_data, current_user_id)
    
    return RedirectResponse(f"/listings/{listing_id}", status_code=303)


# ===== Task 2: Potential Buyers Route =====
@app.get("/api/listings/{listing_id}/potential-buyers")
async def get_potential_buyers(request: Request, listing_id: str):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from api.listings import get_listing_by_id
    listing = await get_listing_by_id(listing_id)
    if not listing:
        return JSONResponse({"error": "Listing not found"}, status_code=404)
    
    if listing.get("user_id") != user.get("id"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    conversations = await rest_select_auth_async("conversations", access_token, filters={"listing_id": f"eq.{listing_id}"})
    
    # Batch fetch all buyer profiles in a single query (fixes N+1)
    buyer_ids = list({conv.get("buyer_id") for conv in conversations if conv.get("buyer_id") and conv.get("buyer_id") != user.get("id")})
    if not buyer_ids:
        return []
    
    profiles = await rest_select_auth_async("profiles", access_token, filters={"user_id": f"in.({','.join(buyer_ids)})"})
    profile_map = {p["user_id"]: p for p in profiles}
    
    potential_buyers = []
    for bid in buyer_ids:
        profile = profile_map.get(bid)
        if profile:
            potential_buyers.append({
                "user_id": bid,
                "name": profile.get("name", "Unknown")
            })
    
    return potential_buyers


# ===== Phone Number Reveal Endpoint =====
@app.get("/api/listings/{listing_id}/phone")
async def get_listing_phone(request: Request, listing_id: str):
    """Fetch seller phone number only when user clicks 'Show Number'."""
    from api.listings import get_listing_by_id
    listing = await get_listing_by_id(listing_id)
    if not listing:
        return JSONResponse({"error": "Listing not found"}, status_code=404)
    
    seller_id = listing.get("user_id")
    if not seller_id:
        return JSONResponse({"phone": None})
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return JSONResponse({"phone": None})
    
    try:
        profile_data = await rest_select_auth_async("profiles", access_token, filters={"user_id": f"eq.{seller_id}"}, columns="phone,show_phone")
        if profile_data:
            profile = profile_data[0]
            if profile.get("show_phone"):
                return JSONResponse({"phone": profile.get("phone")})
    except Exception:
        pass
    
    return JSONResponse({"phone": None})


# ===== Task 2: Mark as Sold Route =====
@app.post("/api/listings/{listing_id}/mark-sold")
async def mark_sold(request: Request, listing_id: str, buyer_id: str = Form(...)):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return JSONResponse({"error": "No access token"}, status_code=401)
    
    from api.listings import get_listing_by_id, update_listing
    listing = await get_listing_by_id(listing_id)
    if not listing:
        return JSONResponse({"error": "Listing not found"}, status_code=404)
    
    current_user_id = user.get("id")
    if listing.get("user_id") != current_user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    if listing.get("status") == "sold":
        return JSONResponse({"error": "Listing already sold"}, status_code=400)
    
    # Update listing status to sold
    await update_listing(listing_id, {"status": "sold"}, current_user_id)
    
    # Create transaction record using authenticated insert
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if transaction already exists for this listing + buyer (async)
    existing_tx = await rest_select_auth_async("transactions", access_token,
        filters={"listing_id": f"eq.{listing_id}", "buyer_id": f"eq.{buyer_id}"})
    if existing_tx and len(existing_tx) > 0:
        logger.info(f"Transaction already exists for listing {listing_id}, buyer {buyer_id}")
        return {"success": True, "message": "Listing already sold"}

    try:
        transaction_data = {
            "listing_id": listing_id,
            "seller_id": current_user_id,
            "buyer_id": buyer_id
        }
        logger.info(f"Creating transaction: {transaction_data}")
        
        result = await rest_insert_auth_async("transactions", access_token, transaction_data)
        logger.info(f"Transaction created successfully: {result}")
        
        if not result or result == {}:
            logger.error("Transaction insert returned empty result")
            return JSONResponse({"error": "Failed to create transaction record"}, status_code=500)
            
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        return JSONResponse({"error": f"Error creating transaction: {str(e)}"}, status_code=500)
    
    return {"success": True, "message": "Listing marked as sold"}


@app.get("/auth/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", {
        "request": request,
        "user": None,
        "now_year": datetime.now().year,
    })


@app.post("/auth/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    from lib.supabase import login_via_rest_async
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Attempting login for: {email}")
        result = await login_via_rest_async(email, password)
        logger.info(f"Login result status: {result.get('error_description', 'ok')}")
        
        if "access_token" in result:
            access_token = result["access_token"]
            refresh_token = result.get("refresh_token", "")
            
            response = RedirectResponse("/", status_code=303)
            response.set_cookie("sb-access-token", access_token, httponly=True, samesite="lax")
            response.set_cookie("sb-refresh-token", refresh_token, httponly=True, samesite="lax")
            logger.info(f"Login successful for: {email}")
            return response
        else:
            error_msg = result.get("error_description", result.get("msg", "Invalid credentials"))
            logger.warning(f"Login failed: {error_msg}")
            return templates.TemplateResponse(request, "auth/login_error.html", {
                "request": request,
                "user": None,
                "error_message": error_msg,
                "now_year": datetime.now().year,
            })
    except Exception as e:
        logger.error(f"Login exception: {e}")
        return templates.TemplateResponse(request, "auth/login_error.html", {
            "request": request,
            "user": None,
            "error_message": str(e),
            "now_year": datetime.now().year,
        })


@app.get("/auth/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "auth/signup.html", {
        "request": request,
        "user": None,
        "now_year": datetime.now().year,
    })


@app.post("/auth/signup")
async def signup(request: Request, name: str = Form(...), mobile: str = Form(""), email: str = Form(...), password: str = Form(...)):
    from lib.supabase import signup_via_rest_async
    import logging
    logger = logging.getLogger(__name__)
    
    if not is_allowed_email_domain(email):
        return templates.TemplateResponse(request, "auth/signup_result.html", {
            "request": request,
            "user": None,
            "success": False,
            "error_message": "Only @novasbe.pt or @unl.pt emails allowed",
            "now_year": datetime.now().year,
        })
    
    try:
        logger.info(f"Signing up user via REST: {email}")
        result = await signup_via_rest_async(email, password, name=name, phone=mobile)
        logger.info(f"Signup result status: {result.get('error_description', 'ok')}")
        
        if "access_token" in result:
            access_token = result["access_token"]
            refresh_token = result.get("refresh_token", "")
            user = result.get("user", {})
            user_id = user.get("id", "") if user else ""
            
            # Create profile with name from form (async)
            if user_id:
                try:
                    profile_data = {
                        "name": name,
                        "phone": mobile,
                        "show_phone": False
                    }
                    logger.info(f"Updating profile with data: {profile_data}")
                    await rest_update_auth_async("profiles", access_token, profile_data, {"user_id": user_id})
                    logger.info(f"Profile updated for user {user_id}")
                except Exception as profile_err:
                    logger.warning(f"Profile update failed: {profile_err}")
            
            response = RedirectResponse("/", status_code=303)
            response.set_cookie("sb-access-token", access_token, httponly=True, samesite="lax")
            response.set_cookie("sb-refresh-token", refresh_token, httponly=True, samesite="lax")
            logger.info(f"Signup successful (auto-confirm), redirecting to home")
            return response
        elif "id" in result:
            user_id_from_signup = result.get("id", "")
            logger.info(f"Signup queued for email confirm: {user_id_from_signup}")
            return templates.TemplateResponse(request, "auth/signup_result.html", {
                "request": request,
                "user": None,
                "success": True,
                "message": "Check your email to confirm your account!",
                "now_year": datetime.now().year,
            })
        else:
            error_msg = result.get("msg", result.get("error_description", "Signup failed"))
            logger.warning(f"Signup failed: {error_msg}")
            return templates.TemplateResponse(request, "auth/signup_result.html", {
                "request": request,
                "user": None,
                "success": False,
                "error_message": error_msg,
                "now_year": datetime.now().year,
            })
    except Exception as e:
        logger.error(f"Signup exception: {e}")
        return templates.TemplateResponse(request, "auth/signup_result.html", {
            "request": request,
            "user": None,
            "success": False,
            "error_message": str(e),
            "now_year": datetime.now().year,
        })


@app.get("/messages")
async def messages_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    user_id = user.get("id", "")
    access_token = request.cookies.get("sb-access-token", "")
    
    from api.messages import get_conversations, get_messages, get_conversation_by_id
    
    conversations = await get_conversations(user_id, access_token) if user_id else []
    
    active_tab = request.query_params.get("tab", "buying")
    selected_chat = request.query_params.get("chat", "")
    
    buying_convs = [c for c in conversations if c.get("is_buying")]
    selling_convs = [c for c in conversations if c.get("is_selling")]
    
    current_convs = buying_convs if active_tab == "buying" else selling_convs
    
    # Find selected conversation and fetch its data
    selected_conv = None
    messages = []
    other_name = ""
    
    if selected_chat:
        selected_conv = next((c for c in conversations if c.get("id") == selected_chat), None)
        if selected_conv:
            messages = await get_messages(selected_chat, access_token)
            other_user_id = selected_conv.get("buyer_id") if selected_conv.get("seller_id") == user_id else selected_conv.get("seller_id")
            from api.profiles import get_profile_by_user_id
            other_profile = await get_profile_by_user_id(other_user_id, access_token)
            other_name = other_profile.get("name", "User") if other_profile else "User"
    
    return templates.TemplateResponse(request, "messages/index.html", {
        "request": request,
        "user": user,
        "conversations": conversations,
        "current_convs": current_convs,
        "buying_convs": buying_convs,
        "selling_convs": selling_convs,
        "active_tab": active_tab,
        "selected_chat": selected_chat,
        "selected_conv": selected_conv,
        "messages": messages,
        "other_name": other_name,
        "user_id": user_id,
        "now_year": datetime.now().year,
    })


@app.get("/messages/{conversation_id}")
async def chat_page(request: Request, conversation_id: str):
    if conversation_id == "new":
        listing_id = request.query_params.get("listing_id", "")
        user = await get_current_user(request)
        if not user:
            return RedirectResponse("/auth/login")
        
        buyer_id = user.get("id", "")
        
        listing = await get_listing_by_id(listing_id) if listing_id else None
        if not listing:
            return templates.TemplateResponse(request, "error.html", {
                "request": request,
                "user": user,
                "title": "Listing not found",
                "message": "The listing you're looking for doesn't exist.",
                "icon": "&#128269;",
                "now_year": datetime.now().year,
            }, status_code=404)
        
        seller_id = listing.get("user_id", "")
        seller_email = listing.get("seller_email", "")
        listing_title = listing.get("title", "")
        
        if buyer_id == seller_id:
            return templates.TemplateResponse(request, "error.html", {
                "request": request,
                "user": user,
                "title": "Cannot message yourself",
                "message": "You are the seller of this listing.",
                "icon": "&#9888;&#65039;",
                "now_year": datetime.now().year,
            }, status_code=400)
        
        return templates.TemplateResponse(request, "messages/new.html", {
            "request": request,
            "user": user,
            "listing_id": listing_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "seller_email": seller_email,
            "listing_title": listing_title,
            "now_year": datetime.now().year,
        })
    
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    user_id = user.get("id", "")
    access_token = request.cookies.get("sb-access-token", "")
    
    from api.messages import get_conversation_by_id, get_messages

    conversation = await get_conversation_by_id(conversation_id, access_token)
    if not conversation:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": user,
            "title": "Conversation not found",
            "message": "The conversation you're looking for doesn't exist.",
            "icon": "&#128269;",
            "now_year": datetime.now().year,
        }, status_code=404)
    
    buyer_id = conversation.get("buyer_id", "")
    seller_id = conversation.get("seller_id", "")
    
    if user_id != buyer_id and user_id != seller_id:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": user,
            "title": "Access Denied",
            "message": "You don't have permission to view this conversation.",
            "icon": "&#128683;",
            "now_year": datetime.now().year,
        }, status_code=403)
    
    listing_id = conversation.get("listing_id", "")
    listing = await get_listing_by_id(listing_id) if listing_id else None
    listing_title = listing.get("title", "Listing") if listing else "Listing"
    
    other_user_id = buyer_id if seller_id == user_id else seller_id
    other_profile = await get_profile_by_user_id(other_user_id, access_token)
    other_name = other_profile.get("name", "User") if other_profile else "User"

    messages = await get_messages(conversation_id, access_token)
    
    return templates.TemplateResponse(request, "messages/conversation.html", {
        "request": request,
        "user": user,
        "conversation": conversation,
        "conversation_id": conversation_id,
        "listing_title": listing_title,
        "listing_id": listing_id,
        "other_user_id": other_user_id,
        "other_name": other_name,
        "messages": messages,
        "user_id": user_id,
        "now_year": datetime.now().year,
    })


@app.get("/messages/new")
async def new_message_page(request: Request, listing_id: str = ""):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    buyer_id = user.get("id", "")
    
    listing = await get_listing_by_id(listing_id) if listing_id else None
    if not listing:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": user,
            "title": "Listing not found",
            "message": "The listing you're looking for doesn't exist.",
            "icon": "&#128269;",
            "now_year": datetime.now().year,
        }, status_code=404)
    
    seller_id = listing.get("user_id", "")
    seller_email = listing.get("seller_email", "")
    listing_title = listing.get("title", "")
    
    if buyer_id == seller_id:
        return templates.TemplateResponse(request, "error.html", {
            "request": request,
            "user": user,
            "title": "Cannot message yourself",
            "message": "You are the seller of this listing.",
            "icon": "&#9888;&#65039;",
            "now_year": datetime.now().year,
        }, status_code=400)
    
    return templates.TemplateResponse(request, "messages/new.html", {
        "request": request,
        "user": user,
        "listing_id": listing_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
        "seller_email": seller_email,
        "listing_title": listing_title,
        "now_year": datetime.now().year,
    })


@app.post("/api/messages")
async def send_message(
    request: Request,
    listing_id: str = Form(...),
    buyer_id: str = Form(...),
    seller_id: str = Form(...),
    content: str = Form(...)
):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    if user.get("id") != buyer_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return RedirectResponse("/auth/login")
    
    from api.messages import create_conversation as create_conv_func, create_message_from_dict as create_msg_func, get_conversation_by_listing_and_buyer
    
    existing_conv = await get_conversation_by_listing_and_buyer(listing_id, buyer_id, access_token)
    
    if existing_conv:
        conversation_id = existing_conv.get("id")
    else:
        from api.messages import ConversationCreate
        conversation_data = ConversationCreate(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=seller_id
        )
        conversation = await create_conv_func(conversation_data, access_token)
        if not conversation or not conversation.get("id"):
            return HTMLResponse("Failed to create conversation", status_code=500)
        conversation_id = conversation["id"]
    
    message_data = {
        "conversation_id": conversation_id,
        "sender_id": buyer_id,
        "content": content
    }
    await create_msg_func(message_data, access_token)
    
    return RedirectResponse("/messages", status_code=303)


@app.post("/api/messages/{conversation_id}")
async def send_chat_message(
    request: Request,
    conversation_id: str,
    user_id: str = Form(...),
    content: str = Form(...),
    active_tab: str = Form("buying")
):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    if user.get("id") != user_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return RedirectResponse("/auth/login")
    
    from api.messages import get_conversation_by_id, create_message_from_dict

    conversation = await get_conversation_by_id(conversation_id, access_token)
    if not conversation:
        return HTMLResponse("Conversation not found", status_code=404)
    
    buyer_id = conversation.get("buyer_id", "")
    seller_id = conversation.get("seller_id", "")
    
    if user_id != buyer_id and user_id != seller_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    message_data = {
        "conversation_id": conversation_id,
        "sender_id": user_id,
        "content": content
    }
    await create_message_from_dict(message_data, access_token)
    
    return RedirectResponse(f"/messages?tab={active_tab}&chat={conversation_id}", status_code=303)


@app.get("/api/messages/{conversation_id}/latest")
async def get_latest_messages(request: Request, conversation_id: str, after: str = ""):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user.get("id", "")
    access_token = request.cookies.get("sb-access-token", "")

    conversation = await get_conversation_by_id(conversation_id, access_token)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    buyer_id = conversation.get("buyer_id", "")
    seller_id = conversation.get("seller_id", "")

    if user_id != buyer_id and user_id != seller_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    filters = {"conversation_id": f"eq.{conversation_id}"}
    if after:
        filters["created_at"] = f"gt.{after}"

    msgs = await rest_select_auth_async("messages", access_token, filters=filters, order="created_at.asc", columns="id,conversation_id,content,created_at,sender_id,read_at")

    return {"messages": msgs}


@app.post("/auth/logout")
async def logout(request: Request):
    from lib.supabase import logout_via_rest_async
    access_token = request.cookies.get("sb-access-token", "")
    
    if access_token:
        try:
            await logout_via_rest_async(access_token)
        except Exception:
            pass
    
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("sb-access-token")
    response.delete_cookie("sb-refresh-token")
    return response


@app.get("/profile/{user_id}")
async def profile_page(request: Request, user_id: str):
    from api.profiles import get_profile_by_user_id, ensure_profile
    from api.listings import get_listings_by_user
    from api.reviews import get_reviews_by_seller, get_average_rating
    from api.messages import get_conversations
    import logging
    logger = logging.getLogger(__name__)
    
    access_token = request.cookies.get("sb-access-token", "")
    
    try:
        await ensure_profile(user_id, access_token)
    except Exception as e:
        logger.error(f"Error ensuring profile: {e}")
    
    try:
        profile = await get_profile_by_user_id(user_id, access_token)
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        profile = None
    
    try:
        listings = await get_listings_by_user(user_id)
    except Exception as e:
        logger.error(f"Error fetching listings: {e}")
        listings = []
    
    access_token = request.cookies.get("sb-access-token", "")
    user_email = ""
    current_user_id = ""
    if access_token:
        from lib.supabase import get_user_via_rest_async
        user_data = await get_user_via_rest_async(access_token)
        if user_data:
            current_user_id = user_data.get("id", "")
            user_email = user_data.get("email", "")
    
    is_own_profile = current_user_id == user_id
    
    reviews = []
    rating = {"average_rating": 0.0, "review_count": 0}
    if not is_own_profile:
        try:
            reviews, rating = await get_reviews_with_average(user_id)
        except Exception as e:
            logger.error(f"Error fetching reviews: {e}")
    
    conversations = []
    if is_own_profile:
        try:
            conversations = await get_conversations(user_id, access_token)
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
    
    purchases = []
    if is_own_profile and access_token:
        try:
            purchases = await rest_select_auth_async("transactions", access_token, filters={"buyer_id": f"eq.{user_id}"}, order="created_at.desc")
            
            all_reviews = await rest_select_auth_async("reviews", access_token, filters={"reviewer_id": f"eq.{user_id}"})
            reviewed_transactions = {r.get("transaction_id") for r in all_reviews if r.get("transaction_id")}

            seen_listings = set()
            unique_purchases = []
            for purchase in purchases:
                lid = purchase.get("listing_id")
                if lid and lid not in seen_listings:
                    seen_listings.add(lid)
                    unique_purchases.append(purchase)
            purchases = unique_purchases

            listing_ids = [p.get("listing_id") for p in purchases if p.get("listing_id")]
            listings_map = {}
            if listing_ids:
                listings_data = await rest_select_async("listings", filters={"id": f"in.({','.join(listing_ids)})"})
                listings_map = {l["id"]: l for l in listings_data}

            for purchase in purchases:
                listing_id = purchase.get("listing_id")
                listing_data = listings_map.get(listing_id)
                if listing_data:
                    purchase["listing_title"] = listing_data.get("title")
                    purchase["listing_price"] = listing_data.get("price")
                    image_urls = listing_data.get("image_urls", [])
                    purchase["listing_image"] = image_urls[0] if image_urls else None
                purchase["transaction_id"] = purchase.get("id")
                purchase["already_reviewed"] = purchase.get("id") in reviewed_transactions
        except Exception as e:
            logger.error(f"Error fetching purchases: {e}")
    
    name = (profile.get("name") or "") if profile else ""
    bio = (profile.get("bio") or "") if profile else ""
    phone = (profile.get("phone") or "") if profile else ""
    show_phone = profile.get("show_phone", False) if profile else False
    avatar_url = profile.get("avatar_url") if profile else None
    created_at = profile.get("created_at", "") if profile else ""
    join_date = ""
    if created_at:
        try:
            join_date = created_at[:7]
        except (ValueError, TypeError, IndexError):
            join_date = created_at
    
    is_editing = request.query_params.get("edit") == "1"
    review_error = request.query_params.get("error")
    
    already_reviewed = False
    can_review = False
    if current_user_id and not is_own_profile and current_user_id != user_id:
        try:
            transactions = await rest_select_auth_async(
                "transactions",
                access_token,
                filters={"buyer_id": f"eq.{current_user_id}", "seller_id": f"eq.{user_id}"}
            )
            can_review = transactions and len(transactions) > 0

            if can_review:
                existing = await rest_select_auth_async(
                    "reviews",
                    access_token,
                    filters={"reviewer_id": f"eq.{current_user_id}"}
                )
                reviewed_tx_ids = {r.get("transaction_id") for r in existing if r.get("transaction_id")}
                unrated_transactions = [t for t in transactions if t.get("id") not in reviewed_tx_ids]
                already_reviewed = len(unrated_transactions) == 0
        except Exception as e:
            logger.error(f"Error checking review eligibility: {e}")
    
    avg_rating_val = rating.get("average_rating", 0)
    review_count = rating.get("review_count", 0)
    
    display_name = name or "Anonymous"
    
    return templates.TemplateResponse(request, "profile/index.html", {
        "request": request,
        "user": await get_current_user(request),
        "profile": profile,
        "user_id": user_id,
        "listings": listings,
        "purchases": purchases,
        "reviews": reviews,
        "rating": rating,
        "name": name,
        "bio": bio,
        "phone": phone,
        "show_phone": show_phone,
        "avatar_url": avatar_url,
        "join_date": join_date,
        "is_own_profile": is_own_profile,
        "is_editing": is_editing,
        "can_review": can_review,
        "already_reviewed": already_reviewed,
        "avg_rating_val": avg_rating_val,
        "review_count": review_count,
        "display_name": display_name,
        "review_error": review_error,
        "current_user_id": current_user_id,
        "now_year": datetime.now().year,
    })


@app.post("/profile/edit")
async def edit_profile(request: Request, avatar: UploadFile = File(None)):
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return RedirectResponse("/auth/login")
    
    # Get current user (async)
    from lib.supabase import get_user_via_rest_async
    user_data = await get_user_via_rest_async(access_token)
    if not user_data:
        return RedirectResponse("/auth/login")
    
    user_id = user_data.get("id", "")
    if not user_id:
        return RedirectResponse("/auth/login")
    
    # Parse form data
    form = await request.form()
    name = form.get("name", "")
    bio = form.get("bio", "")
    phone = form.get("phone", "")
    show_phone = form.get("show_phone") == "on"
    
    # Handle avatar upload
    avatar_url = None
    try:
        if avatar and avatar.filename:
            contents = await avatar.read()
            if contents:
                file_name = avatar.filename or "avatar.jpg"
                avatar_url = await upload_image_async(contents, file_name, bucket="avatars", access_token=access_token)
    except Exception as e:
        print(f"Avatar upload error: {e}")
    
    # Build update data
    update_data = {
        "name": name,
        "bio": bio,
        "phone": phone,
        "show_phone": show_phone
    }
    if avatar_url:
        update_data["avatar_url"] = avatar_url
    
    # Update profile via REST API (authenticated, async)
    try:
        result = await rest_update_auth_async("profiles", access_token, update_data, {"user_id": user_id})
    except Exception as e:
        print(f"Profile update error: {e}")
    
    return RedirectResponse(f"/profile/{user_id}", status_code=302)


@app.post("/reviews")
async def submit_review(request: Request):
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Get current user (async)
    from lib.supabase import get_user_via_rest_async
    user_data = await get_user_via_rest_async(access_token)
    if not user_data:
        return RedirectResponse("/auth/login", status_code=303)
    
    current_user_id = user_data.get("id", "")
    
    if not current_user_id:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Parse form data
    form = await request.form()
    seller_id = form.get("seller_id", "")
    rating = form.get("rating", "0")
    comment = form.get("comment", "")
    transaction_id = form.get("transaction_id", "") or None

    try:
        rating_int = int(rating)
    except (ValueError, TypeError):
        rating_int = 0

    if not seller_id or rating_int == 0:
        return RedirectResponse(f"/profile/{seller_id}", status_code=303)

    # Can't review yourself
    if seller_id == current_user_id:
        return RedirectResponse(f"/profile/{seller_id}", status_code=303)

    # Validate transaction if transaction_id is provided (async)
    if transaction_id:
        tx_filter = {"id": f"eq.{transaction_id}", "buyer_id": f"eq.{current_user_id}", "seller_id": f"eq.{seller_id}"}
    else:
        tx_filter = {"buyer_id": f"eq.{current_user_id}", "seller_id": f"eq.{seller_id}"}
    transactions = await rest_select_auth_async(
        "transactions",
        access_token,
        filters=tx_filter
    )
    if not transactions or len(transactions) == 0:
        return RedirectResponse(f"/profile/{seller_id}?error=not_a_buyer", status_code=303)

    # Check if already reviewed this transaction (async)
    rev_filter = {"reviewer_id": f"eq.{current_user_id}"}
    if transaction_id:
        rev_filter["transaction_id"] = f"eq.{transaction_id}"
    else:
        rev_filter["seller_id"] = f"eq.{seller_id}"
    existing_reviews = await rest_select_auth_async(
        "reviews",
        access_token,
        filters=rev_filter
    )
    if existing_reviews and len(existing_reviews) > 0:
        return RedirectResponse(f"/profile/{seller_id}?error=already_reviewed", status_code=303)

    try:
        insert_data = {
            "reviewer_id": current_user_id,
            "seller_id": seller_id,
            "rating": rating_int,
            "comment": comment or None
        }
        if transaction_id:
            insert_data["transaction_id"] = transaction_id
        result = await rest_insert_auth_async("reviews", access_token, insert_data)
        if not result:
            return RedirectResponse(f"/profile/{seller_id}?error=review_failed", status_code=303)
    except Exception as e:
        print(f"Review submit error: {e}")
        return RedirectResponse(f"/profile/{seller_id}?error=review_failed", status_code=303)

    return RedirectResponse(f"/profile/{seller_id}", status_code=303)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "Nova Exchange"}
