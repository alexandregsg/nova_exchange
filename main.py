# Nova-Exchange FastAPI Application
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from typing import List
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from lib.supabase import init_supabase, get_db, is_allowed_email_domain

# Create FastAPI app
app = FastAPI(
    title="Nova Exchange",
    description="Nova SBE Marketplace for Students",
    version="1.0.0"
)

# Initialize Supabase
init_supabase()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return HTMLResponse(
        render_page(
            f'''
            <div class="min-h-[60vh] flex items-center justify-center">
                <div class="text-center">
                    <div class="text-6xl mb-4">😵</div>
                    <h1 class="text-2xl font-bold text-gray-900 mb-2">Something went wrong</h1>
                    <p class="text-gray-600 mb-6">We encountered an unexpected error. Please try again.</p>
                    <a href="/" class="inline-block bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700">
                        Go Home
                    </a>
                </div>
            </div>''',
            "Error - Nova Exchange"
        ),
        status_code=500
    )

@app.get("/error/{code}")
async def error_page(code: int):
    """Custom error pages"""
    errors = {
        404: ("Page Not Found", "The page you're looking for doesn't exist.", "🔍"),
        403: ("Access Denied", "You don't have permission to view this page.", "🚫"),
        500: ("Server Error", "Something went wrong on our end.", "😵"),
    }
    title, message, icon = errors.get(code, ("Error", "An error occurred.", "⚠️"))
    return HTMLResponse(
        render_page(
            f'''
            <div class="min-h-[60vh] flex items-center justify-center">
                <div class="text-center">
                    <div class="text-6xl mb-4">{icon}</div>
                    <h1 class="text-2xl font-bold text-gray-900 mb-2">{title}</h1>
                    <p class="text-gray-600 mb-6">{message}</p>
                    <a href="/" class="inline-block bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700">
                        Go Home
                    </a>
                </div>
            </div>''',
            f"{title} - Nova Exchange"
        ),
        status_code=code
    )

# Import API functions
from api.listings import get_featured_listings, search_listings, get_listing_by_id, get_listings_by_user, create_listing as create_listing_func, ListingInput
from api.profiles import get_profile_by_user_id, ensure_profile
from api.messages import get_conversations, get_conversations_optimized, get_messages, get_conversation_by_id, create_message, MessageCreate
from api.reviews import get_reviews_by_seller, get_average_rating
from lib.auth import get_current_user
from lib.components import listing_card, conversation_card, empty_state, star_rating


# ==================== SHARED HTML TEMPLATES ====================

async def get_navbar(request: Request) -> str:
    user = await get_current_user(request)
    access_token = request.cookies.get("sb-access-token", "") or None
    
    if user:
        user_id = user.get("id", "")
        try:
            profile = get_profile_by_user_id(user_id, access_token) if user_id else None
        except Exception:
            profile = None
        email = user.get("email", "User")
        user_name = (profile.get("name") if profile else None) or email.split("@")[0] if "@" in email else email
        avatar_url = profile.get("avatar_url") if profile else None
        
        avatar_html = f'<img src="{avatar_url}" class="h-8 w-8 rounded-full object-cover" loading="lazy">' if avatar_url else ''
        
        return f"""
<nav class="bg-white border-b border-gray-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <a href="/" class="text-xl font-bold text-emerald-600">Nova Exchange</a>
        <div class="hidden sm:ml-8 sm:flex sm:space-x-8">
          <a href="/browse" class="text-gray-900 hover:text-emerald-600 px-3 py-2 text-sm font-medium">Browse</a>
          <a href="/listings/new" class="text-gray-900 hover:text-emerald-600 px-3 py-2 text-sm font-medium">Sell</a>
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <a href="/messages" class="text-gray-500 hover:text-emerald-600">Messages</a>
        <a href="/profile/{user_id}" class="text-gray-500 hover:text-emerald-600 flex items-center gap-2">
          {avatar_html}
          {user_name}
        </a>
        <form action="/auth/logout" method="POST" style="display:inline">
          <button type="submit" class="text-gray-500 hover:text-emerald-600 text-sm">Logout</button>
        </form>
      </div>
    </div>
  </div>
</nav>"""
    
    return """
<nav class="bg-white border-b border-gray-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <a href="/" class="text-xl font-bold text-emerald-600">Nova Exchange</a>
        <div class="hidden sm:ml-8 sm:flex sm:space-x-8">
          <a href="/browse" class="text-gray-900 hover:text-emerald-600 px-3 py-2 text-sm font-medium">Browse</a>
          <a href="/auth/login" class="text-gray-900 hover:text-emerald-600 px-3 py-2 text-sm font-medium">Sell</a>
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <a href="/messages" class="text-gray-500 hover:text-emerald-600">Messages</a>
        <a href="/auth/login" class="text-gray-500 hover:text-emerald-600 text-sm">Login</a>
        <a href="/auth/signup" class="bg-emerald-600 text-white px-4 py-2 rounded-md text-sm hover:bg-emerald-700">Sign Up</a>
      </div>
    </div>
  </div>
</nav>"""

FOOTER = f"""
<footer class="bg-white border-t border-gray-200 mt-auto">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <p class="text-center text-gray-500 text-sm">&copy; {__import__("datetime").datetime.now().year} Nova Exchange. Nova SBE Marketplace.</p>
  </div>
</footer>
"""

STYLES = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href='https://unpkg.com/lucide-static@0.469.0/font/lucide.min.css' />
<script>
// Form validation
function validateForm(formId, rules) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    form.addEventListener('submit', function(e) {
        let isValid = true;
        for (const [fieldId, rule] of Object.entries(rules)) {
            const field = document.getElementById(fieldId);
            if (!field) continue;
            const value = field.value.trim();
            let error = null;
            
            if (rule.required && !value) {
                error = rule.required;
            } else if (rule.min && parseFloat(value) < rule.min) {
                error = rule.min;
            } else if (rule.pattern && !rule.pattern.test(value)) {
                error = rule.patternMsg;
            }
            
            if (error) {
                e.preventDefault();
                showFieldError(fieldId, error);
                isValid = false;
            } else {
                clearFieldError(fieldId);
            }
        }
        return isValid;
    });
}

function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    let errorEl = document.getElementById(fieldId + '-error');
    if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.id = fieldId + '-error';
        errorEl.className = 'text-red-600 text-sm mt-1';
        field.parentNode.insertBefore(errorEl, field.nextSibling);
    }
    errorEl.textContent = typeof message === 'string' ? message : 'Invalid value';
    field.classList.add('border-red-500');
}

function clearFieldError(fieldId) {
    const errorEl = document.getElementById(fieldId + '-error');
    if (errorEl) errorEl.remove();
    const field = document.getElementById(fieldId);
    if (field) field.classList.remove('border-red-500');
}

// Create listing validation
function validateCreateListing() {
    let isValid = true;
    
    const title = document.getElementById('title');
    const price = document.getElementById('price');
    const condition = document.getElementById('condition');
    
    clearFieldError('title');
    clearFieldError('price');
    clearFieldError('condition');
    
    if (!title || !title.value.trim()) {
        showFieldError('title', 'Title is required');
        isValid = false;
    }
    
    if (!price || parseFloat(price.value) <= 0) {
        showFieldError('price', 'Price must be greater than 0');
        isValid = false;
    }
    
    if (!condition || !condition.value) {
        showFieldError('condition', 'Please select a condition');
        isValid = false;
    }
    
    return isValid;
}

// Login validation
function validateLogin() {
    let isValid = true;
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    
    clearFieldError('email');
    clearFieldError('password');
    
    if (!email || !email.value.trim()) {
        showFieldError('email', 'Email is required');
        isValid = false;
    } else if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
        showFieldError('email', 'Please enter a valid email');
        isValid = false;
    }
    
    if (!password || !password.value) {
        showFieldError('password', 'Password is required');
        isValid = false;
    }
    
    return isValid;
}

// Signup validation
function validateSignup() {
    let isValid = true;
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    const confirm = document.getElementById('confirm-password');
    
    clearFieldError('email');
    clearFieldError('password');
    clearFieldError('confirm-password');
    
    if (!email || !email.value.trim()) {
        showFieldError('email', 'Email is required');
        isValid = false;
    } else if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
        showFieldError('email', 'Please enter a valid email');
        isValid = false;
    }
    
    if (!password || password.value.length < 6) {
        showFieldError('password', 'Password must be at least 6 characters');
        isValid = false;
    }
    
    if (confirm && password && password.value !== confirm.value) {
        showFieldError('confirm-password', 'Passwords do not match');
        isValid = false;
    }
    
    return isValid;
}

// Review validation
function validateReview() {
    const rating = document.getElementById('rating-value');
    const errorEl = document.getElementById('rating-error');
    
    if (!rating || !rating.value) {
        if (errorEl) errorEl.classList.remove('hidden');
        return false;
    }
    if (errorEl) errorEl.classList.add('hidden');
    return true;
}

function setRating(value) {
    document.getElementById('rating-value').value = value;
    const stars = document.querySelectorAll('.star-btn');
    stars.forEach((star, index) => {
        star.style.color = index < value ? '#f59e0b' : '#d1d5db';
    });
}
</script>
<style>
/* Toast animations */
.toast-enter { animation: slideIn 0.3s ease-out; }
.toast-exit { animation: slideOut 0.3s ease-in; }
@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
@keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}
/* Back to top */
.back-to-top { transition: all 0.2s ease; }
.back-to-top:hover { transform: translateY(-2px); }
/* Card transitions */
.card-hover { transition: all 0.2s ease; }
.card-hover:hover { transform: translateY(-2px); }
/* Button transitions */
.btn-transition { transition: all 0.15s ease; }
.btn-transition:active { transform: scale(0.98); }
/* Modal fade */
.modal-fade { animation: fadeIn 0.2s ease-out; }
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
</style>
<script>
function showToast(message, type) {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = 'toast-enter px-4 py-2 rounded-lg shadow-lg ' + (type === 'success' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove('toast-enter');
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2';
    document.body.appendChild(container);
    return container;
}
function showDeleteModal(itemType, onConfirm) {
    document.getElementById('delete-item-type').textContent = itemType;
    document.getElementById('delete-confirm-btn').onclick = function() { eval(onConfirm); };
    document.getElementById('delete-modal').classList.remove('hidden');
}
function closeDeleteModal() {
    document.getElementById('delete-modal').classList.add('hidden');
}
</script>
<!-- Delete Modal Template -->
<div id="delete-modal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center modal-fade">
    <div class="bg-white rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
        <h3 class="text-lg font-semibold mb-2">Delete <span id="delete-item-type">this item</span>?</h3>
        <p class="text-gray-600 mb-4">This action cannot be undone.</p>
        <div class="flex gap-2">
            <button id="delete-confirm-btn" class="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 btn-transition">
                Delete
            </button>
            <button onclick="closeDeleteModal()" class="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300 btn-transition">
                Cancel
            </button>
        </div>
    </div>
</div>
"""


def render_page(content: str, title: str = "Nova Exchange", navbar: str = None, add_back_to_top: bool = False) -> str:
    if navbar is None:
        navbar = navbar
    back_to_top_btn = ""
    if add_back_to_top:
        back_to_top_btn = '''
    <button onclick="window.scrollTo({top:0,behavior:'smooth'})" 
        class="fixed bottom-6 right-6 bg-emerald-600 text-white w-12 h-12 rounded-full shadow-lg hover:bg-emerald-700 flex items-center justify-center text-xl z-40 back-to-top">
        ↑
    </button>'''
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {STYLES}
</head>
<body class="bg-gray-50 min-h-screen flex flex-col">
    {navbar}
    <main class="flex-grow">
        {content}
    </main>
    {FOOTER}
    {back_to_top_btn}
</body>
</html>"""


# ==================== ROUTES ====================

@app.get("/")
async def home(request: Request):
    from lib.supabase import rest_select
    
    # Get featured listings (limited to 6 for display)
    try:
        featured = get_featured_listings(6)
    except Exception as e:
        print(f"Error: {e}")
        featured = []

    total_active = len(featured)
    
    # Create listing cards using component
    listing_cards = ""
    for i, listing in enumerate(featured):
        listing_cards += listing_card(listing, index=i)
    
    if not listing_cards:
        listing_cards = empty_state("No listings yet", "Be the first to list an item!", "📦", "/listings/new", "Start Selling")
    
    content = f"""
    <section class="border-b border-gray-200" style="background-image: radial-gradient(circle, #e2e8f0 1px, transparent 1px); background-size: 24px 24px;">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20 lg:py-24">
            <div class="flex flex-col items-center gap-12">
                <div class="w-full text-center">
                    <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-gray-900">
                        Buy & sell within<br>
                        <span class="text-emerald-600">Nova SBE</span>
                    </h1>
                    <p class="mt-4 text-base sm:text-lg text-gray-600 max-w-lg mx-auto">
                        The student marketplace for textbooks, electronics, furniture, and more — all within the Nova SBE community.
                    </p>
                    <form action="/browse" method="GET" class="mt-8 flex gap-2 max-w-xl mx-auto">
                        <div class="relative flex-1">
                            <input type="text" name="q" placeholder="Find textbooks, calculators, or dorm gear..." 
                                class="w-full pl-4 h-12 text-base border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500">
                        </div>
                        <button type="submit" class="h-12 px-6 bg-emerald-600 text-white rounded-md hover:bg-emerald-700">
                            Search
                        </button>
                    </form>
                    <div class="mt-3 flex items-center justify-center gap-2">
                        <span class="relative flex h-2.5 w-2.5">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                        </span>
                        <span class="text-xs text-gray-500">{total_active} items listed</span>
                    </div>
                    <div class="mt-8 flex items-center justify-center flex-wrap gap-2">
                        <a href="/browse?category=Textbooks" class="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium hover:shadow-sm">
                            <span class="inline-flex items-center justify-center h-6 w-6 rounded-md bg-blue-50 text-blue-700">📚</span>
                            Textbooks
                        </a>
                        <a href="/browse?category=Electronics" class="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium hover:shadow-sm">
                            <span class="inline-flex items-center justify-center h-6 w-6 rounded-md bg-violet-50 text-violet-700">💻</span>
                            Electronics
                        </a>
                        <a href="/browse?category=Furniture" class="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium hover:shadow-sm">
                            <span class="inline-flex items-center justify-center h-6 w-6 rounded-md bg-emerald-50 text-emerald-700">🪑</span>
                            Furniture
                        </a>
                        <a href="/browse?category=Other" class="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium hover:shadow-sm">
                            <span class="inline-flex items-center justify-center h-6 w-6 rounded-md bg-amber-50 text-amber-700">📦</span>
                            Other
                        </a>
                    </div>
                    <div class="mt-8">
                        <a href="/listings/new" class="inline-flex items-center gap-2 h-12 px-6 bg-emerald-600 text-white rounded-md hover:bg-emerald-700">
                            Start selling
                            <span>→</span>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </section>
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Featured Listings</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {listing_cards}
        </div>
    </section>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Nova Exchange - Buy & Sell at Nova SBE", navbar))


@app.get("/browse")
async def browse(request: Request, q: str = "", category: str = "", condition: str = "", 
             sort: str = "created_desc", min_price: Optional[str] = None, max_price: Optional[str] = None):
    try:
        min_p = float(min_price) if min_price and min_price.strip() else None
        max_p = float(max_price) if max_price and max_price.strip() else None
        results = search_listings(q, category or None, condition or None, sort, min_p, max_p)
    except Exception:
        results = []
    
    count = len(results)
    
    # Create listing cards using component
    listing_cards = ""
    for i, listing in enumerate(results):
        listing_cards += listing_card(listing, index=i)
    
    if not listing_cards:
        listing_cards = empty_state("No listings found", "Try different filters or create a listing", "📦", "/listings/new", "Create Listing")
    
    content = f"""
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">Browse Listings</h1>
        <div class="flex flex-col md:flex-row gap-8">
            <aside class="md:w-64 flex-shrink-0">
                <form method="GET" class="space-y-6">
                    <div>
                        <label for="q" class="block text-sm font-medium text-gray-700 mb-1">Search</label>
                        <input type="text" name="q" id="q" value="{q}" class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="Search...">
                    </div>
                    <div>
                        <label for="category" class="block text-sm font-medium text-gray-700 mb-1">Category</label>
                        <select name="category" id="category" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                            <option value="">All Categories</option>
                            <option value="Textbooks" {"selected" if category == "Textbooks" else ""}>Textbooks</option>
                            <option value="Electronics" {"selected" if category == "Electronics" else ""}>Electronics</option>
                            <option value="Furniture" {"selected" if category == "Furniture" else ""}>Furniture</option>
                            <option value="Clothing" {"selected" if category == "Clothing" else ""}>Clothing</option>
                            <option value="Sports" {"selected" if category == "Sports" else ""}>Sports</option>
                            <option value="Music" {"selected" if category == "Music" else ""}>Music</option>
                            <option value="Transportation" {"selected" if category == "Transportation" else ""}>Transportation</option>
                            <option value="Household" {"selected" if category == "Household" else ""}>Household</option>
                            <option value="Other" {"selected" if category == "Other" else ""}>Other</option>
                        </select>
                    </div>
                    <div>
                        <label for="condition" class="block text-sm font-medium text-gray-700 mb-1">Condition</label>
                        <select name="condition" id="condition" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                            <option value="">All Conditions</option>
                            <option value="New" {"selected" if condition == "New" else ""}>New</option>
                            <option value="Like New" {"selected" if condition == "Like New" else ""}>Like New</option>
                            <option value="Good" {"selected" if condition == "Good" else ""}>Good</option>
                            <option value="Fair" {"selected" if condition == "Fair" else ""}>Fair</option>
                            <option value="Poor" {"selected" if condition == "Poor" else ""}>Poor</option>
                        </select>
                    </div>
                    <div>
                        <label for="sort" class="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
                        <select name="sort" id="sort" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                            <option value="created_desc" {"selected" if sort == "created_desc" else ""}>Newest First</option>
                            <option value="created_asc" {"selected" if sort == "created_asc" else ""}>Oldest First</option>
                            <option value="price_asc" {"selected" if sort == "price_asc" else ""}>Price: Low to High</option>
                            <option value="price_desc" {"selected" if sort == "price_desc" else ""}>Price: High to Low</option>
                        </select>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label for="min_price" class="block text-sm font-medium text-gray-700 mb-1">Min Price</label>
                            <input type="number" name="min_price" id="min_price" min="0" step="0.01" class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="0">
                        </div>
                        <div>
                            <label for="max_price" class="block text-sm font-medium text-gray-700 mb-1">Max Price</label>
                            <input type="number" name="max_price" id="max_price" min="0" step="0.01" class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="Any">
                        </div>
                    </div>
                    <button type="submit" class="w-full bg-emerald-600 text-white px-4 py-2 rounded-md hover:bg-emerald-700">
                        Apply Filters
                    </button>
                </form>
            </aside>
            <div class="flex-grow">
                <p class="text-gray-500 mb-4">{count} results</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {listing_cards}
                </div>
            </div>
        </div>
    </div>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Browse - Nova Exchange", navbar))


@app.get("/listings/new")
async def create_listing_page(request: Request):
    content = """
    <div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">Create a New Listing</h1>
        <form id="create-listing-form" method="POST" action="/api/listings" enctype="multipart/form-data" class="space-y-6" onsubmit="return handleCreateListingSubmit(event)">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Photos (max 3)</label>
                <div class="grid grid-cols-3 gap-4" id="create-image-container">
                    <label class="cursor-pointer border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center hover:border-emerald-500 transition-colors" id="create-add-1" style="display: flex; aspect-ratio: 1/1">
                        <input type="file" name="image_1" accept="image/*" class="hidden" id="file-input-1" onchange="handleFileSelect(this, 1)">
                        <span class="text-4xl">+</span>
                        <span class="text-sm text-gray-500 mt-1">Photo 1</span>
                    </label>
                    <label class="cursor-pointer border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center hover:border-emerald-500 transition-colors" id="create-add-2" style="display: flex; aspect-ratio: 1/1">
                        <input type="file" name="image_2" accept="image/*" class="hidden" id="file-input-2" onchange="handleFileSelect(this, 2)">
                        <span class="text-4xl">+</span>
                        <span class="text-sm text-gray-500 mt-1">Photo 2</span>
                    </label>
                    <label class="cursor-pointer border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center hover:border-emerald-500 transition-colors" id="create-add-3" style="display: flex; aspect-ratio: 1/1">
                        <input type="file" name="image_3" accept="image/*" class="hidden" id="file-input-3" onchange="handleFileSelect(this, 3)">
                        <span class="text-4xl">+</span>
                        <span class="text-sm text-gray-500 mt-1">Photo 3</span>
                    </label>
                </div>
                <p class="text-xs text-gray-500 mt-1">Click each box to add up to 3 photos (optional)</p>
            </div>
            <div>
                <label for="title" class="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                <input type="text" name="title" id="title" required maxlength="200" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <div>
                <label for="description" class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea name="description" id="description" rows="4" class="w-full px-3 py-2 border border-gray-300 rounded-md"></textarea>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label for="price" class="block text-sm font-medium text-gray-700 mb-1">Price (EUR) *</label>
                    <input type="number" name="price" id="price" required min="0.01" step="0.01" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                </div>
                <div>
                    <label for="condition" class="block text-sm font-medium text-gray-700 mb-1">Condition *</label>
                    <select name="condition" id="condition" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                        <option value="">Select condition</option>
                        <option value="New">New</option>
                        <option value="Like New">Like New</option>
                        <option value="Good">Good</option>
                        <option value="Fair">Fair</option>
                        <option value="Poor">Poor</option>
                    </select>
                </div>
            </div>
            <div>
                <label for="category" class="block text-sm font-medium text-gray-700 mb-1">Category *</label>
                <select name="category" id="category" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                    <option value="">Select category</option>
                    <option value="Textbooks">Textbooks</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Furniture">Furniture</option>
                    <option value="Clothing">Clothing</option>
                    <option value="Sports">Sports</option>
                    <option value="Music">Music</option>
                    <option value="Transportation">Transportation</option>
                    <option value="Household">Household</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            <div>
                <label for="location" class="block text-sm font-medium text-gray-700 mb-1">Location</label>
                <input type="text" name="location" id="location" placeholder="Campus, residence hall, etc." class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <button type="submit" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
                Create Listing
            </button>
        </form>
    </div>
    <script>
    // Store selected files
    var selectedFiles = {1: null, 2: null, 3: null};
    
    function handleFileSelect(input, slotNum) {
        var file = input.files[0];
        if (!file) return;
        
        selectedFiles[slotNum] = file;
        
        var reader = new FileReader();
        reader.onload = function(e) {
            var label = document.getElementById('create-add-' + slotNum);
            var spanPlus = label.querySelector('.text-4xl');
            var spanText = label.querySelector('.text-sm');
            
            // Update label to show filled state
            spanPlus.textContent = '\u2713';
            spanPlus.className = 'text-3xl text-emerald-600';
            spanText.textContent = 'Filled';
            spanText.className = 'text-xs text-emerald-600 mt-1';
            
            // Remove existing image if any
            var existingImg = label.querySelector('img.preview-img');
            if (existingImg) existingImg.remove();
            
            // Add preview image
            var img = document.createElement('img');
            img.src = e.target.result;
            img.className = 'preview-img w-full h-full object-cover rounded-lg';
            img.style.position = 'absolute';
            img.style.top = '0';
            img.style.left = '0';
            label.style.position = 'relative';
            label.insertBefore(img, label.firstChild);
            
            // Disable input to prevent re-selection
            input.disabled = true;
            label.style.cursor = 'default';
            label.style.borderColor = '#10b981';
        };
        reader.readAsDataURL(file);
    }
    
    function handleCreateListingSubmit(event) {
        var title = document.getElementById('title');
        var price = document.getElementById('price');
        var condition = document.getElementById('condition');
        
        if (!title || !title.value.trim()) {
            alert('Title is required');
            return false;
        }
        
        if (!price || parseFloat(price.value) <= 0) {
            alert('Price must be greater than 0');
            return false;
        }
        
        if (!condition || !condition.value) {
            alert('Please select a condition');
            return false;
        }
        
        event.preventDefault();
        
        var form = document.getElementById('create-listing-form');
        var formData = new FormData(form);
        
        // Only include selected files (not empty ones from disabled inputs)
        if (selectedFiles[1]) formData.set('image_1', selectedFiles[1]);
        if (selectedFiles[2]) formData.set('image_2', selectedFiles[2]);
        if (selectedFiles[3]) formData.set('image_3', selectedFiles[3]);
        
        fetch('/api/listings', {
            method: 'POST',
            body: formData,
            redirect: 'follow'
        }).then(function(response) {
            if (response.status === 303 || response.status === 200 || response.redirected || response.ok) {
                window.location.href = '/browse';
            } else {
                alert('Error creating listing');
            }
        }).catch(function(err) {
            alert('Error: ' + err.message);
        });
        
        return false;
    }
    </script>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Create Listing - Nova Exchange", navbar))


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
    from lib.supabase import upload_image
    
    access_token = request.cookies.get("sb-access-token", "")
    
    if not access_token:
        return RedirectResponse("/auth/login")
    
    from lib.supabase import get_user_via_rest
    user_data = get_user_via_rest(access_token)
    
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
                    image_url = upload_image(contents, file_name)
                    if image_url:
                        image_urls.append(image_url)
            except Exception as e:
                print(f"Image upload error: {e}")
    
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
    listing = create_listing_func(listing_input)
    
    if listing and listing.get('id'):
        lid = listing.get('id', '')
        return RedirectResponse(f"/listings/{lid}", status_code=303)
    else:
        # Listing creation might have failed
        return RedirectResponse("/browse", status_code=303)


@app.get("/listings/{listing_id}")
async def listing_detail(request: Request, listing_id: str):
    listing = get_listing_by_id(listing_id)
    if not listing:
        return HTMLResponse("""
        <!DOCTYPE html><html><body><h1>Listing not found</h1><a href="/">Go home</a></body></html>
        """)

    seller_profile = listing.get('profiles') if listing else None

    title = listing.get('title', 'Untitled')
    price = listing.get('price', 0)
    desc = listing.get('description', 'No description')
    condition = listing.get('condition', 'N/A')
    category = listing.get('category', 'Other')
    location = listing.get('location', '')
    seller = listing.get('seller_email', '')
    seller_id = listing.get('user_id', '')
    created = listing.get('created_at', '')[:10] if listing.get('created_at') else ''

    seller_phone = seller_profile.get("phone") if seller_profile else None
    seller_show_phone = seller_profile.get("show_phone", False) if seller_profile else False
    seller_name = seller_profile.get("name") if seller_profile else None
    if not seller_name:
        seller_name = seller
    seller_avatar_url = seller_profile.get("avatar_url") if seller_profile else None
    seller_join_date = seller_profile.get("created_at", "")[:10] if seller_profile and seller_profile.get("created_at") else "Recently"
    
    user = await get_current_user(request)
    current_user_id = user.get('id', '') if user else ''
    is_seller = current_user_id and current_user_id == seller_id
    
    # Check listing status
    listing_status = listing.get('status', 'active')
    is_sold = listing_status == 'sold'
    
    # Status badge
    status_badge = ""
    if is_sold:
        status_badge = '<span class="bg-red-100 text-red-800 px-3 py-1 rounded-full font-medium">SOLD</span>'
    
    contact_button = ""
    edit_button = ""
    mark_sold_button = ""
    
    if user and is_seller and not is_sold:
        edit_button = f"""
        <a href="/listings/{listing_id}/edit" class="mt-4 inline-block w-full bg-gray-600 text-white px-6 py-3 rounded-lg text-center hover:bg-gray-700">
            Edit Listing
        </a>
        <button type="button" onclick="openMarkSoldModal()" class="mt-2 inline-block w-full bg-red-600 text-white px-6 py-3 rounded-lg text-center hover:bg-red-700">
            Mark as Sold
        </button>
        """
    elif user and is_seller and is_sold:
        edit_button = f"""
        <a href="/listings/{listing_id}/edit" class="mt-4 inline-block w-full bg-gray-600 text-white px-6 py-3 rounded-lg text-center hover:bg-gray-700">
            Edit Listing
        </a>
        """
    elif user and not is_seller and not is_sold:
        contact_button = f"""
        <a href="/messages/new?listing_id={listing_id}" class="mt-6 inline-block w-full bg-emerald-600 text-white px-6 py-3 rounded-lg text-center hover:bg-emerald-700">
            Contact Seller
        </a>
        """
    elif is_sold:
        contact_button = '<p class="mt-6 text-gray-500 text-center">This item has been sold</p>'
    
    # OLX-style "Show Number" button
    show_number_button = ""
    if seller_show_phone and seller_phone and not is_seller and not is_sold and user:
        show_number_button = f"""
        <button type="button" id="reveal-phone-btn" onclick="revealPhoneNumber()" class="mt-3 inline-block w-full border border-emerald-600 text-emerald-600 px-6 py-3 rounded-lg text-center hover:bg-emerald-50">
            <span id="phone-btn-text">📱 Show Number</span>
            <span id="phone-btn-number" style="display:none">{seller_phone}</span>
        </button>
        """
    
    image_urls_raw = listing.get('image_urls')
    print(f"DEBUG image_urls_raw: {image_urls_raw} (type: {type(image_urls_raw)})")
    import json
    image_urls = []
    
    if image_urls_raw:
        if isinstance(image_urls_raw, list):
            image_urls = image_urls_raw
            print(f"DEBUG image_urls from list: {image_urls}")
        elif isinstance(image_urls_raw, str):
            try:
                image_urls = json.loads(image_urls_raw)
                print(f"DEBUG image_urls from JSON: {image_urls}")
            except:
                if image_urls_raw.startswith('{') and image_urls_raw.endswith('}'):
                    image_urls = [u.strip().strip('"') for u in image_urls_raw[1:-1].split(',') if u.strip()]
                else:
                    image_urls = [image_urls_raw]
    
    print(f"DEBUG final image_urls: {image_urls}")
    
    image_html = ""
    if image_urls:
        if len(image_urls) == 1:
            image_html = f'''
            <div class="relative rounded-lg overflow-hidden cursor-pointer" onclick="openFullscreen(0)" style="aspect-ratio: 4/3">
                <img src="{image_urls[0]}" class="w-full h-full object-contain">
            </div>
            '''
        else:
            image_html = f'''
            <div class="relative rounded-lg overflow-hidden" style="aspect-ratio: 4/3" id="image-gallery">
                <div class="absolute inset-0 w-full h-full">
                    <img src="{image_urls[0]}" class="w-full h-full object-contain" id="gallery-image" loading="lazy">
                </div>
                <button id="nav-left" onclick="changeImage(-1)" class="absolute left-2 top-1/2 -translate-y-1/2 bg-white/80 rounded-full p-2 hover:bg-white">←</button>
                <button id="nav-right" onclick="changeImage(1)" class="absolute right-2 top-1/2 -translate-y-1/2 bg-white/80 rounded-full p-2 hover:bg-white">→</button>
                <div class="absolute bottom-2 left-1/2 -translate-x-1/2 bg-black/50 text-white px-2 py-1 rounded text-sm" id="image-counter">1 / {len(image_urls)}</div>
            </div>
            <script>
            var currentImage = 0;
            var images = {json.dumps(image_urls)};
            var totalImages = images.length;
            function updateNav() {{
                document.getElementById('gallery-image').src = images[currentImage];
                document.getElementById('image-counter').textContent = (currentImage + 1) + ' / ' + totalImages;
                document.getElementById('nav-left').style.visibility = (currentImage > 0) ? 'visible' : 'hidden';
                document.getElementById('nav-right').style.visibility = (currentImage < totalImages - 1) ? 'visible' : 'hidden';
            }}
            function changeImage(direction) {{
                if (direction === -1 && currentImage > 0) {{
                    currentImage--;
                }} else if (direction === 1 && currentImage < totalImages - 1) {{
                    currentImage++;
                }}
                updateNav();
            }}
            function openFullscreen(index) {{
                currentImage = index;
                document.getElementById('fullscreen-image').src = images[currentImage];
                document.getElementById('fullscreen-modal').style.display = 'flex';
            }}
            function closeFullscreen() {{
                document.getElementById('fullscreen-modal').style.display = 'none';
            }}
            updateNav();
            </script>
            <div id="fullscreen-modal" class="fixed inset-0 bg-black z-50 hidden flex-col items-center justify-center" onclick="closeFullscreen()">
                <button class="absolute top-4 right-4 text-white text-4xl" onclick="event.stopPropagation(); closeFullscreen()">×</button>
                <button class="absolute left-4 top-1/2 -translate-y-1/2 text-white text-4xl" onclick="event.stopPropagation(); changeImage(-1)">←</button>
                <img src="" class="max-h-screen max-w-full object-contain" id="fullscreen-image" onclick="event.stopPropagation()">
                <button class="absolute right-4 top-1/2 -translate-y-1/2 text-white text-4xl" onclick="event.stopPropagation(); changeImage(1)">→</button>
            </div>
            '''
    else:
        image_html = '''
        <div class="bg-gray-200 rounded-lg flex items-center justify-center" style="aspect-ratio: 4/3">
            <span class="text-6xl">📦</span>
        </div>
        '''
    
    content = f"""
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
                {image_html}
            </div>
            <div>
                <h1 class="text-3xl font-bold text-gray-900">{title}</h1>
                <p class="text-3xl font-bold text-emerald-600 mt-2">€{price}</p>
                <div class="mt-4 flex gap-2 flex-wrap">
                    {status_badge}
                    <span class="bg-gray-100 px-3 py-1 rounded">{condition}</span>
                    <span class="bg-gray-100 px-3 py-1 rounded">{category}</span>
                </div>
                {f'<p class="mt-4 text-gray-600"><span class="font-medium">Location:</span> {location}</p>' if location else ''}
                <div class="mt-6">
                    <h2 class="text-lg font-semibold text-gray-900">Description</h2>
                    <p class="mt-2 text-gray-600">{desc}</p>
                </div>
                <a href="/profile/{seller_id}" class="block mt-6 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all duration-200">
                    <div class="flex items-center gap-4">
                        <div class="h-14 w-14 rounded-full bg-emerald-100 flex items-center justify-center overflow-hidden flex-shrink-0">
                            {f'<img src="{seller_avatar_url}" class="h-full w-full object-cover" loading="lazy">' if seller_avatar_url else f'<span class="text-emerald-600 font-semibold text-xl">{seller_name[0].upper() if seller_name else "?"}</span>'}
                        </div>
                        <div>
                            <p class="text-lg font-bold text-gray-900">{seller_name}</p>
                            <p class="text-sm text-gray-500">Member since {seller_join_date}</p>
                        </div>
                    </div>
                </a>
                {edit_button}
                {contact_button}
                {show_number_button}
            </div>
        </div>
    </div>
    
    <!-- Mark Sold Modal -->
    <div id="mark-sold-modal" class="fixed inset-0 bg-black/50 z-50 hidden flex items-center justify-center">
        <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Mark as Sold</h3>
                <button type="button" onclick="closeMarkSoldModal()" class="text-gray-500 text-2xl">&times;</button>
            </div>
            <p class="text-gray-600 mb-4">Select the buyer for this listing:</p>
            <select id="buyer-select" class="w-full px-3 py-2 border border-gray-300 rounded-md mb-4">
                <option value="">Loading...</option>
            </select>
            <button type="button" onclick="confirmSale()" id="confirm-sale-btn" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
                Confirm Sale
            </button>
            <p id="mark-sold-error" class="text-red-500 text-sm mt-2 hidden"></p>
        </div>
    </div>
    
<script>
    var LISTING_ID = "{listing_id}";
    
    function openMarkSoldModal() {{
        var modal = document.getElementById("mark-sold-modal");
        if (modal) {{
            modal.classList.remove("hidden");
        }}
        loadPotentialBuyers();
    }}
    
    function closeMarkSoldModal() {{
        var modal = document.getElementById("mark-sold-modal");
        if (modal) {{
            modal.classList.add("hidden");
        }}
    }}
    
    function loadPotentialBuyers() {{
        var select = document.getElementById("buyer-select");
        if (!select) return;
        select.innerHTML = '<option value="">Loading...</option>';
        
        var apiUrl = "/api/listings/" + LISTING_ID + "/potential-buyers";
        fetch(apiUrl).then(function(r) {{ return r.json(); }}).then(function(buyers) {{
            if (!buyers || buyers.length === 0) {{
                select.innerHTML = '<option value="">No potential buyers found</option>';
                return;
            }}
            var html = "";
            for (var i = 0; i < buyers.length; i++) {{
                var b = buyers[i];
                html += '<option value="' + b.user_id + '">' + (b.name || "Unknown") + '</option>';
            }}
            select.innerHTML = html;
        }}).catch(function(err) {{
            select.innerHTML = '<option value="">Error loading buyers</option>';
        }});
    }}
    
    function confirmSale() {{
        var buyerId = document.getElementById("buyer-select").value;
        if (!buyerId) {{
            alert("Please select a buyer");
            return;
        }}
        
        var btn = document.getElementById("confirm-sale-btn");
        var errorEl = document.getElementById("mark-sold-error");
        btn.disabled = true;
        btn.textContent = "Processing...";
        
        var formData = new FormData();
        formData.append("buyer_id", buyerId);
        
        fetch("/api/listings/" + LISTING_ID + "/mark-sold", {{
            method: "POST",
            body: formData
        }}).then(function(r) {{ return r.json(); }}).then(function(result) {{
            if (result.success) {{
                window.location.reload();
            }} else {{
                errorEl.textContent = result.error || "Error marking as sold";
                errorEl.classList.remove("hidden");
                btn.disabled = false;
                btn.textContent = "Confirm Sale";
            }}
        }}).catch(function(err) {{
            errorEl.textContent = "Error: " + err.message;
            errorEl.classList.remove("hidden");
            btn.disabled = false;
            btn.textContent = "Confirm Sale";
        }});
    }}
    
    function revealPhoneNumber() {{
        var btnText = document.getElementById('phone-btn-text');
        var btnNumber = document.getElementById('phone-btn-number');
        if (btnText && btnNumber) {{
            btnText.style.display = 'none';
            btnNumber.style.display = 'inline';
            document.getElementById('reveal-phone-btn').onclick = null;
        }}
    }}
    </script>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, f"{title} - Nova Exchange", navbar))


@app.get("/listings/{listing_id}/edit")
async def edit_listing_page(request: Request, listing_id: str):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    listing = get_listing_by_id(listing_id)
    if not listing:
        return HTMLResponse("""
        <!DOCTYPE html><html><body><h1>Listing not found</h1><a href="/">Go home</a></body></html>
        """)
    
    current_user_id = user.get('id', '')
    seller_id = listing.get('user_id', '')
    
    if current_user_id != seller_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    title = listing.get('title', '')
    desc = listing.get('description', '') or ''
    price = listing.get('price', 0)
    condition = listing.get('condition', '')
    category = listing.get('category', '')
    location = listing.get('location', '') or ''
    import json
    image_urls = listing.get('image_urls', []) or []
    if image_urls and isinstance(image_urls, str):
        try:
            image_urls = json.loads(image_urls)
        except:
            image_urls = [image_urls]
    
    content = f"""
    <div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">Edit Listing</h1>
        <form method="POST" action="/api/listings/{listing_id}/edit" enctype="multipart/form-data" class="space-y-6" id="edit-listing-form">
            <input type="hidden" name="existing_images" id="existing-images" value="{','.join(image_urls)}">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Photos (max 3)</label>
                <div class="flex flex-wrap gap-3" id="image-preview-container">
                </div>
                <button type="button" id="add-photo-btn" class="mt-2 cursor-pointer w-24 h-24 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center hover:border-emerald-500 hover:text-emerald-500 transition-colors">
                    <span class="text-3xl">+</span>
                </button>
                <input type="file" id="image-input" accept="image/jpeg,image/png,image/webp,image/gif" class="hidden" multiple>
                <p class="text-xs text-gray-500 mt-1">Click to upload photos (max 3 total)</p>
                <p id="upload-status" class="text-xs text-gray-500 mt-1 hidden">Uploading...</p>
            </div>
            <div>
                <label for="title" class="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                <input type="text" name="title" id="title" required maxlength="200" class="w-full px-3 py-2 border border-gray-300 rounded-md" value="{title}">
            </div>
            <div>
                <label for="description" class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea name="description" id="description" rows="4" class="w-full px-3 py-2 border border-gray-300 rounded-md">{desc}</textarea>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label for="price" class="block text-sm font-medium text-gray-700 mb-1">Price (EUR) *</label>
                    <input type="number" name="price" id="price" required min="0.01" step="0.01" class="w-full px-3 py-2 border border-gray-300 rounded-md" value="{price}">
                </div>
                <div>
                    <label for="condition" class="block text-sm font-medium text-gray-700 mb-1">Condition *</label>
                    <select name="condition" id="condition" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                        <option value="New" {'selected="selected"' if condition == "New" else ""}>New</option>
                        <option value="Like New" {'selected="selected"' if condition == "Like New" else ""}>Like New</option>
                        <option value="Good" {'selected="selected"' if condition == "Good" else ""}>Good</option>
                        <option value="Fair" {'selected="selected"' if condition == "Fair" else ""}>Fair</option>
                        <option value="Poor" {'selected="selected"' if condition == "Poor" else ""}>Poor</option>
                    </select>
                </div>
            </div>
            <div>
                <label for="category" class="block text-sm font-medium text-gray-700 mb-1">Category *</label>
                <select name="category" id="category" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                    <option value="Textbooks" {'selected="selected"' if category == "Textbooks" else ""}>Textbooks</option>
                    <option value="Electronics" {'selected="selected"' if category == "Electronics" else ""}>Electronics</option>
                    <option value="Furniture" {'selected="selected"' if category == "Furniture" else ""}>Furniture</option>
                    <option value="Clothing" {'selected="selected"' if category == "Clothing" else ""}>Clothing</option>
                    <option value="Sports" {'selected="selected"' if category == "Sports" else ""}>Sports</option>
                    <option value="Music" {'selected="selected"' if category == "Music" else ""}>Music</option>
                    <option value="Transportation" {'selected="selected"' if category == "Transportation" else ""}>Transportation</option>
                    <option value="Household" {'selected="selected"' if category == "Household" else ""}>Household</option>
                    <option value="Other" {'selected="selected"' if category == "Other" else ""}>Other</option>
                </select>
            </div>
            <div>
                <label for="location" class="block text-sm font-medium text-gray-700 mb-1">Location</label>
                <input type="text" name="location" id="location" placeholder="Campus, residence hall, etc." class="w-full px-3 py-2 border border-gray-300 rounded-md" value="{location}">
            </div>
            <button type="submit" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
                Save Changes
            </button>
        </form>
</div>
    <script>
    var existingImages = {json.dumps(image_urls)};
    if (!Array.isArray(existingImages)) existingImages = [];
    var allImageUrls = {json.dumps(image_urls)}.slice();
    var supabaseUrl = "{os.getenv('NEXT_PUBLIC_SUPABASE_URL', '')}";
    var supabaseKey = "{os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY', '')}";
    
    function renderImages() {{
        var container = document.getElementById('image-preview-container');
        var addBtn = document.getElementById('add-photo-btn');
        if (!container) return;
        
        container.querySelectorAll('.preview-item').forEach(el => el.remove());
        
        allImageUrls.forEach(function(url, idx) {{
            var div = document.createElement('div');
            div.className = 'preview-item relative w-24 h-24 rounded-lg overflow-hidden border border-gray-200 group';
            div.innerHTML = '<img src="' + url + '" class="w-full h-full object-cover"><button type="button" onclick="removeImage(' + idx + ')" class="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity">×</button>';
            container.appendChild(div);
        }});
        
        if (addBtn) {{
            addBtn.style.display = allImageUrls.length >= 3 ? 'none' : 'inline-flex';
        }}
        
        document.getElementById('existing-images').value = allImageUrls.join(',');
    }}
    
    function removeImage(index) {{
        if (index >= allImageUrls.length) return;
        allImageUrls.splice(index, 1);
        renderImages();
    }}
    
    document.getElementById('add-photo-btn').addEventListener('click', function() {{
        document.getElementById('image-input').click();
    }});
    
    document.getElementById('image-input').addEventListener('change', async function(e) {{
        var files = e.target.files;
        if (!files || files.length === 0) return;
        
        var remaining = 3 - allImageUrls.length;
        var filesToUpload = Array.from(files).slice(0, remaining);
        
        if (filesToUpload.length === 0) return;
        
        var statusEl = document.getElementById("upload-status");
        statusEl.textContent = "Uploading...";
        statusEl.classList.add("visible");
        
        for (var i = 0; i < filesToUpload.length; i++) {{
            var file = filesToUpload[i];
            
            if (!file.type.match(/^image\/(jpeg|png|webp|gif)$/)) {{
                alert('Invalid file type. Use JPEG, PNG, WebP, or GIF.');
                continue;
            }}
            
            if (file.size > 5 * 1024 * 1024) {{
                alert('File too large. Maximum 5MB.');
                continue;
            }}
            
            try {{
                var fileName = '{listing_id}/' + Date.now() + '-' + Math.random().toString(36).substring(7) + '.' + file.name.split('.').pop();
                
                var response = await fetch(supabaseUrl + '/storage/v1/object/listing-images/' + fileName, {{
                    method: 'POST',
                    headers: {{
                        'Authorization': 'Bearer ' + supabaseKey,
                        'Content-Type': file.type
                    }},
                    body: file
                }});
                
                if (response.ok) {{
                    var publicUrl = supabaseUrl + '/storage/v1/object/public/listing-images/' + fileName;
                    allImageUrls.push(publicUrl);
                }}
            }} catch (err) {{
                console.error('Upload error:', err);
            }}
        }}
        
        statusEl.classList.add("hidden");
        renderImages();
        e.target.value = "";
    }});
    
    renderImages();
    </script>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Edit Listing - Nova Exchange", navbar))


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
    
    listing = get_listing_by_id(listing_id)
    if not listing:
        return HTMLResponse("Listing not found", status_code=404)
    
    current_user_id = user.get('id', '')
    seller_id = listing.get('user_id', '')
    
    if current_user_id != seller_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    from lib.supabase import upload_image
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
                    image_url = upload_image(contents, file_name)
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
                print(f"DEBUG Image {idx+1}: filename={file_name}, size={len(contents)}")
                
                image_url = upload_image(contents, file_name)
                print(f"DEBUG Image {idx+1} uploaded: {image_url}")
                
                if image_url:
                    image_urls.append(image_url)
                    print(f"DEBUG Added to image_urls, total: {len(image_urls)}")
            except Exception as e:
                print(f"Image upload error: {e}")
    
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
    update_listing(listing_id, update_data, current_user_id)
    
    return RedirectResponse(f"/listings/{listing_id}", status_code=303)


# ===== Task 2: Potential Buyers Route =====
@app.get("/api/listings/{listing_id}/potential-buyers")
async def get_potential_buyers(request: Request, listing_id: str):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from api.listings import get_listing_by_id
    listing = get_listing_by_id(listing_id)
    if not listing:
        return JSONResponse({"error": "Listing not found"}, status_code=404)
    
    if listing.get("user_id") != user.get("id"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from lib.supabase import rest_select_auth
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    conversations = rest_select_auth("conversations", access_token, filters={"listing_id": f"eq.{listing_id}"})
    
    potential_buyers = []
    seen_ids = set()
    for conv in conversations:
        buyer_id = conv.get("buyer_id")
        if buyer_id and buyer_id != user.get("id") and buyer_id not in seen_ids:
            seen_ids.add(buyer_id)
            profiles = rest_select_auth("profiles", access_token, filters={"user_id": f"eq.{buyer_id}"})
            if profiles:
                potential_buyers.append({
                    "user_id": buyer_id,
                    "name": profiles[0].get("name", "Unknown")
                })
    
    return potential_buyers


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
    listing = get_listing_by_id(listing_id)
    if not listing:
        return JSONResponse({"error": "Listing not found"}, status_code=404)
    
    current_user_id = user.get("id")
    if listing.get("user_id") != current_user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    if listing.get("status") == "sold":
        return JSONResponse({"error": "Listing already sold"}, status_code=400)
    
    # Update listing status to sold
    update_listing(listing_id, {"status": "sold"}, current_user_id)
    
    # Create transaction record using authenticated insert
    import logging
    logger = logging.getLogger(__name__)
    
    from lib.supabase import rest_insert_auth
    try:
        transaction_data = {
            "listing_id": listing_id,
            "seller_id": current_user_id,
            "buyer_id": buyer_id
        }
        logger.info(f"Creating transaction: {transaction_data}")
        
        result = rest_insert_auth("transactions", access_token, transaction_data)
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
    content = """
    <div class="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-8 text-center">Login to Nova Exchange</h1>
        <form method="POST" action="/auth/login" class="space-y-6" onsubmit="return validateLogin()">
            <div>
                <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" name="email" id="email" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <div>
                <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" name="password" id="password" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <button type="submit" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
                Login
            </button>
        </form>
        <p class="mt-4 text-center text-gray-500">
            Don't have an account? <a href="/auth/signup" class="text-emerald-600 hover:underline">Sign up</a>
        </p>
    </div>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Login - Nova Exchange", navbar))


@app.post("/auth/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    from lib.supabase import login_via_rest
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Attempting login for: {email}")
        result = login_via_rest(email, password)
        logger.info(f"Login result: {result}")
        
        # Check for access_token in response
        if "access_token" in result:
            access_token = result["access_token"]
            refresh_token = result.get("refresh_token", "")
            user = result.get("user", {})
            
            response = RedirectResponse("/", status_code=303)
            response.set_cookie("sb-access-token", access_token, httponly=True, samesite="lax")
            response.set_cookie("sb-refresh-token", refresh_token, httponly=True, samesite="lax")
            logger.info(f"Login successful for: {email}")
            return response
        else:
            # Login failed - show error
            error_msg = result.get("error_description", result.get("msg", "Invalid credentials"))
            logger.warning(f"Login failed: {error_msg}")
            navbar = await get_navbar(request)
            return HTMLResponse(render_page(f"""
            <div class="max-w-md mx-auto px-4 py-8">
                <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">Login failed: {error_msg}</div>
                <a href="/auth/login" class="text-emerald-600 hover:underline">Try again</a>
            </div>
            """, "Login Error - Nova Exchange"), navbar=navbar)
    except Exception as e:
        logger.error(f"Login exception: {e}")
        navbar = await get_navbar(request)
        return HTMLResponse(render_page(f"""
        <div class="max-w-md mx-auto px-4 py-8">
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">Login failed: {str(e)}</div>
            <a href="/auth/login" class="text-emerald-600 hover:underline">Try again</a>
        </div>
        """, "Login Error - Nova Exchange", navbar=navbar))


@app.get("/auth/signup")
async def signup_page(request: Request):
    content = """
    <div class="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-8 text-center">Sign Up for Nova Exchange</h1>
        <form method="POST" action="/auth/signup" class="space-y-6" onsubmit="return validateSignup()">
            <div>
                <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input type="text" name="name" id="name" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <div>
                <label for="mobile" class="block text-sm font-medium text-gray-700 mb-1">Mobile Number</label>
                <input type="tel" name="mobile" id="mobile" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <div>
                <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input type="email" name="email" id="email" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                <p class="mt-1 text-sm text-gray-500">Must be @novasbe.pt or @unl.pt</p>
            </div>
            <div>
                <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" name="password" id="password" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <div>
                <label for="confirm-password" class="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                <input type="password" name="confirm-password" id="confirm-password" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <button type="submit" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
                Sign Up
            </button>
        </form>
        <p class="mt-4 text-center text-gray-500">
            Already have an account? <a href="/auth/login" class="text-emerald-600 hover:underline">Login</a>
        </p>
    </div>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Sign Up - Nova Exchange", navbar))


@app.post("/auth/signup")
async def signup(request: Request, name: str = Form(...), mobile: str = Form(""), email: str = Form(...), password: str = Form(...)):
    from lib.supabase import signup_via_rest
    import logging
    logger = logging.getLogger(__name__)
    
    if not is_allowed_email_domain(email):
        navbar = await get_navbar(request)
        return HTMLResponse(render_page("""
        <div class="max-w-md mx-auto px-4 py-8">
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">Only @novasbe.pt or @unl.pt emails allowed</div>
            <a href="/auth/signup" class="text-emerald-600 hover:underline">Try again</a>
        </div>
        """, "Signup Error - Nova Exchange", navbar=navbar))
    
    try:
        logger.info(f"Signing up user via REST: {email} with name={name}, phone={mobile}")
        result = signup_via_rest(email, password, name=name, phone=mobile)
        logger.info(f"Signup result: {result}")
        
        # Check for access_token (auto-confirm) or user (needs email confirm)
        if "access_token" in result:
            # Auto-confirmed - set cookies
            access_token = result["access_token"]
            refresh_token = result.get("refresh_token", "")
            user = result.get("user", {})
            user_id = user.get("id", "") if user else ""
            
            # Create profile with name from form - update existing or insert new
            if user_id:
                from lib.supabase import rest_update_auth
                try:
                    profile_data = {
                        "name": name,
                        "phone": mobile,
                        "show_phone": False
                    }
                    print(f"DEBUG SIGNUP: mobile='{mobile}', profile_data={profile_data}")
                    logger.info(f"Updating profile with data: {profile_data}")
                    updated = rest_update_auth("profiles", access_token, profile_data, {"user_id": user_id})
                    logger.info(f"Profile updated for user {user_id}: {updated}")
                except Exception as profile_err:
                    logger.warning(f"Profile update failed: {profile_err}")
            
            response = RedirectResponse("/", status_code=303)
            response.set_cookie("sb-access-token", access_token, httponly=True, samesite="lax")
            response.set_cookie("sb-refresh-token", refresh_token, httponly=True, samesite="lax")
            logger.info(f"Signup successful (auto-confirm), redirecting to home")
            return response
        elif "id" in result:
            # Email confirmation required - create profile now so data isn't lost
            # Note: We don't have access_token here, so this uses the auth trigger approach
            # The profile will be created by the trigger on first login after email confirmation
            user_id_from_signup = result.get("id", "")
            logger.info(f"Signup queued for email confirm: {user_id_from_signup}, name={name}")
            navbar = await get_navbar(request)
            return HTMLResponse(render_page("""
            <div class="max-w-md mx-auto px-4 py-8">
                <div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">Check your email to confirm your account!</div>
                <a href="/" class="text-emerald-600 hover:underline">Go to Home</a>
            </div>
            """, "Signup Success - Nova Exchange", navbar=navbar))
        else:
            # Signup failed
            error_msg = result.get("msg", result.get("error_description", "Signup failed"))
            logger.warning(f"Signup failed: {error_msg}")
            navbar = await get_navbar(request)
            return HTMLResponse(render_page(f"""
            <div class="max-w-md mx-auto px-4 py-8">
                <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">Signup failed: {error_msg}</div>
                <a href="/auth/signup" class="text-emerald-600 hover:underline">Try again</a>
            </div>
            """, "Signup Error - Nova Exchange", navbar=navbar))
    except Exception as e:
        logger.error(f"Signup exception: {e}")
        navbar = await get_navbar(request)
        return HTMLResponse(render_page(f"""
        <div class="max-w-md mx-auto px-4 py-8">
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">Signup failed: {str(e)}</div>
            <a href="/auth/signup" class="text-emerald-600 hover:underline">Try again</a>
        </div>
        """, "Signup Error - Nova Exchange", navbar=navbar))


@app.get("/messages")
async def messages_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    user_id = user.get("id", "")
    access_token = request.cookies.get("sb-access-token", "")
    
    from api.messages import get_conversations, get_messages, get_conversation_by_id
    
    conversations = get_conversations(user_id, access_token) if user_id else []
    
    active_tab = request.query_params.get("tab", "buying")
    selected_chat = request.query_params.get("chat", "")
    
    buying_convs = [c for c in conversations if c.get("is_buying")]
    selling_convs = [c for c in conversations if c.get("is_selling")]
    
    current_convs = buying_convs if active_tab == "buying" else selling_convs
    
    def render_conv_item(conv, is_selected):
        conv_id = conv.get("id", "")
        avatar_url = conv.get("other_user_avatar_url") or ""
        name = conv.get("other_user_name", "User")
        listing_title = conv.get("listing_title", "Listing")
        last_msg = conv.get("last_message", "")
        unread = conv.get("unread_count", 0)
        thumb = conv.get("listing_thumbnail")
        
        avatar_html = f'<img src="{avatar_url}" class="w-12 h-12 rounded-full object-cover bg-gray-200" loading="lazy">' if avatar_url else f'<div class="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 font-semibold">{name[0].upper() if name else "?"}</div>'

        thumb_html = f'<img src="{thumb}" class="w-12 h-12 rounded object-cover ml-2 flex-shrink-0" loading="lazy">' if thumb else ''
        
        selected_class = "bg-gray-100" if is_selected else "hover:bg-gray-50"
        
        return f'''
        <a href="?tab={active_tab}&chat={conv_id}" class="flex items-center p-3 border-b {selected_class} transition-colors">
            {avatar_html}
            <div class="flex-1 min-w-0 ml-3">
                <div class="flex justify-between items-center">
                    <span class="font-medium text-gray-900 truncate">{name}</span>
                    {f'<span class="w-2 h-2 bg-emerald-500 rounded-full flex-shrink-0"></span>' if unread > 0 else ''}
                </div>
                <p class="text-xs text-gray-500 truncate">{listing_title}</p>
                <p class="text-sm text-gray-600 truncate">{last_msg or "No messages yet"}</p>
            </div>
            {thumb_html}
        </a>
        '''
    
    conv_list_html = "".join([render_conv_item(c, c.get("id") == selected_chat) for c in current_convs])
    
    chat_area_html = ""
    if selected_chat and conversations:
        selected_conv = next((c for c in conversations if c.get("id") == selected_chat), None)
        if selected_conv:
            messages_list = get_messages(selected_chat, access_token)
            
            buyer_id = selected_conv.get("buyer_id", "")
            seller_id = selected_conv.get("seller_id", "")
            listing_title = selected_conv.get("listing_title", "Listing")
            listing_id = selected_conv.get("listing_id", "")
            
            other_user_id = buyer_id if seller_id == user_id else seller_id
            from api.profiles import get_profile_by_user_id
            other_profile = get_profile_by_user_id(other_user_id)
            other_name = other_profile.get("name", "User") if other_profile else "User"
            
            messages_html = ""
            for msg in messages_list:
                sender_id = msg.get("sender_id", "")
                content = msg.get("content", "")
                is_mine = sender_id == user_id
                created_at = msg.get("created_at", "")[:16] if msg.get("created_at") else ""
                
                msg_class = "ml-auto bg-emerald-100" if is_mine else "mr-auto bg-white"
                messages_html += f'''
                <div class="flex {"justify-end" if is_mine else "justify-start"} mb-3">
                    <div class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg {msg_class} shadow-sm">
                        <p class="text-gray-800">{content}</p>
                        <p class="text-xs text-gray-400 mt-1 text-right">{created_at}</p>
                    </div>
                </div>
                '''
            
            chat_area_html = f'''
            <div class="flex flex-col h-full">
                <div class="p-4 border-b bg-white shadow-sm">
                    <div class="flex items-center gap-3">
                        <div class="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center">
                            <span class="text-emerald-600 font-semibold">{other_name[0].upper() if other_name else "?"}</span>
                        </div>
                        <div class="flex-1">
                            <h2 class="text-lg font-semibold text-gray-900">
                                <a href="/listings/{listing_id}" class="text-gray-900 hover:text-emerald-700 hover:underline">{listing_title}</a>
                            </h2>
                            <div class="text-sm text-gray-500">Chat with {other_name}</div>
                        </div>
                    </div>
                </div>
                <div class="flex-1 overflow-y-auto p-4" id="chat-messages">
                    {messages_html if messages_html else '<p class="text-gray-400 text-center py-8">No messages yet. Start the conversation!</p>'}
                </div>
                <form action="/api/messages/{selected_chat}" method="POST" class="p-4 border-t bg-white">
                    <input type="hidden" name="user_id" value="{user_id}">
                    <input type="hidden" name="active_tab" value="{active_tab}">
                    <div class="flex gap-2">
                        <input type="text" name="content" placeholder="Type a message..." class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500" required>
                        <button type="submit" class="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium">Send</button>
                    </div>
                </form>
            </div>
            '''
    else:
        chat_area_html = '''
        <div class="flex items-center justify-center h-full text-gray-400">
            <div class="text-center">
                <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                </svg>
                <p class="text-lg">Select a conversation to start chatting</p>
            </div>
        </div>
        '''
    
    buying_active = "text-emerald-600 border-b-2 border-emerald-600" if active_tab == "buying" else "text-gray-500 hover:text-gray-700"
    selling_active = "text-emerald-600 border-b-2 border-emerald-600" if active_tab == "selling" else "text-gray-500 hover:text-gray-700"
    
    content = f'''
    <div class="max-w-7xl mx-auto px-0 sm:px-0 lg:px-0 py-0">
        <div class="flex h-[calc(100vh-64px)] bg-white shadow-lg rounded-lg overflow-hidden ml-4 mr-4 mt-4">
            <!-- Left Sidebar -->
            <div class="w-80 flex-shrink-0 border-r bg-gray-50 flex flex-col">
                <!-- Tabs -->
                <div class="flex border-b bg-white">
                    <a href="?tab=buying" class="flex-1 py-3 text-center font-medium text-sm {buying_active} transition-colors">
                        Buying ({len(buying_convs)})
                    </a>
                    <a href="?tab=selling" class="flex-1 py-3 text-center font-medium text-sm {selling_active} transition-colors">
                        Selling ({len(selling_convs)})
                    </a>
                </div>
                
                <!-- Conversation List -->
                <div class="flex-1 overflow-y-auto">
                    {conv_list_html if conv_list_html else f'''
                    <div class="p-4 text-center text-gray-500">
                        <p class="mb-2">No conversations yet</p>
                        <a href="/browse" class="text-emerald-600 hover:text-emerald-700 text-sm">Browse listings</a>
                    </div>
                    '''}
                </div>
            </div>
            
            <!-- Right Chat Area -->
            <div class="flex-1 bg-gray-50">
                {chat_area_html}
            </div>
        </div>
    </div>
    '''
    
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Messages - Nova Exchange", navbar))


@app.get("/messages/{conversation_id}")
async def chat_page(request: Request, conversation_id: str):
    # Handle /messages/new specially - inline (not redirect to avoid loop)
    if conversation_id == "new":
        listing_id = request.query_params.get("listing_id", "")
        user = await get_current_user(request)
        if not user:
            return RedirectResponse("/auth/login")
        
        buyer_id = user.get("id", "")
        
        listing = get_listing_by_id(listing_id) if listing_id else None
        if not listing:
            return HTMLResponse("""
            <!DOCTYPE html><html><body><h1>Listing not found</h1><a href="/browse">Browse listings</a></body></html>
            """)
        
        seller_id = listing.get("user_id", "")
        seller_email = listing.get("seller_email", "")
        listing_title = listing.get("title", "")
        
        if buyer_id == seller_id:
            return HTMLResponse("""
            <!DOCTYPE html><html><body><h1>Cannot message yourself</h1><p>You are the seller of this listing.</p><a href="/browse">Browse listings</a></body></html>
            """)
        
        navbar = await get_navbar(request)
        content = f"""
        <div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <h1 class="text-3xl font-bold text-gray-900 mb-8">Contact Seller</h1>
            <div class="bg-white shadow rounded-lg p-6">
                <div class="mb-6 p-4 bg-gray-50 rounded-lg">
                    <p class="text-sm text-gray-500">Regarding:</p>
                    <p class="text-lg font-semibold">{listing_title}</p>
                    <p class="text-sm text-gray-500">Seller: {seller_email}</p>
                </div>
                <form action="/api/messages" method="POST">
                    <input type="hidden" name="listing_id" value="{listing_id}">
                    <input type="hidden" name="buyer_id" value="{buyer_id}">
                    <input type="hidden" name="seller_id" value="{seller_id}">
                    <div class="mb-6">
                        <label for="content" class="block text-sm font-medium text-gray-700 mb-2">Message</label>
                        <textarea name="content" id="content" rows="6" required class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="Hi, I'm interested in this item..."></textarea>
                    </div>
                    <button type="submit" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700">
                        Send Message
                    </button>
                </form>
            </div>
        </div>
        """
        return HTMLResponse(render_page(content, "Contact Seller - Nova Exchange", navbar))
    
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    user_id = user.get("id", "")
    access_token = request.cookies.get("sb-access-token", "")
    
    from api.messages import get_conversation_by_id, get_messages
    
    conversation = get_conversation_by_id(conversation_id, access_token)
    if not conversation:
        return HTMLResponse("""
        <!DOCTYPE html><html><body><h1>Conversation not found</h1><a href="/messages">Back to messages</a></body></html>
        """, status_code=404)
    
    buyer_id = conversation.get("buyer_id", "")
    seller_id = conversation.get("seller_id", "")
    
    if user_id != buyer_id and user_id != seller_id:
        return HTMLResponse("Unauthorized", status_code=401)
    
    listing_id = conversation.get("listing_id", "")
    listing = get_listing_by_id(listing_id) if listing_id else None
    listing_title = listing.get("title", "Listing") if listing else "Listing"
    
    other_user_id = buyer_id if seller_id == user_id else seller_id
    from api.profiles import get_profile_by_user_id
    other_profile = get_profile_by_user_id(other_user_id)
    other_name = other_profile.get("name", "User") if other_profile else "User"
    
    messages = get_messages(conversation_id, access_token) if access_token else get_messages(conversation_id)
    
    messages_html = ""
    for msg in messages:
        sender_id = msg.get("sender_id", "")
        content = msg.get("content", "")
        is_mine = sender_id == user_id
        created_at = msg.get("created_at", "")[:16] if msg.get("created_at") else ""
        
        msg_class = "ml-auto bg-emerald-100" if is_mine else "mr-auto bg-gray-100"
        messages_html += f'''
        <div class="flex {'justify-end' if is_mine else 'justify-start'} mb-3">
            <div class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg {msg_class}">
                <p class="text-gray-800">{content}</p>
                <p class="text-xs text-gray-500 mt-1">{created_at}</p>
            </div>
        </div>
        '''
    
    content = f"""
    <div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <a href="/messages" class="text-emerald-600 hover:text-emerald-700 mb-4 inline-block">&larr; Back to Messages</a>
        <h1 class="text-2xl font-bold text-gray-900 mb-2">{listing_title}</h1>
        <a href="/profile/{other_user_id}" class="inline-flex items-center gap-2 mb-6 text-gray-500 hover:text-emerald-600">
            <div class="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center hover:ring-2 hover:ring-emerald-500">
                <span class="text-emerald-600">{other_name[0].upper()}</span>
            </div>
            <span>Chat with {other_name}</span>
        </a>
        
        <div class="bg-white shadow rounded-lg p-4 mb-4" style="min-height: 400px; max-height: 500px; overflow-y: auto;">
            {messages_html if messages_html else '<p class="text-gray-500 text-center py-8">No messages yet. Start the conversation!</p>'}
        </div>
        
        <form action="/api/messages/{conversation_id}" method="POST" class="flex gap-2">
            <input type="hidden" name="conversation_id" value="{conversation_id}">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="text" name="content" placeholder="Type a message..." class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500" required>
            <button type="submit" class="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">Send</button>
        </form>
    </div>
    """
    
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, f"Chat - Nova Exchange", navbar))


@app.get("/messages/new")
async def new_message_page(request: Request, listing_id: str = ""):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login")
    
    buyer_id = user.get("id", "")
    
    listing = get_listing_by_id(listing_id) if listing_id else None
    if not listing:
        return HTMLResponse("""
        <!DOCTYPE html><html><body><h1>Listing not found</h1><a href="/browse">Browse listings</a></body></html>
        """)
    
    seller_id = listing.get("user_id", "")
    seller_email = listing.get("seller_email", "")
    listing_title = listing.get("title", "")
    
    if buyer_id == seller_id:
        return HTMLResponse("""
        <!DOCTYPE html><html><body><h1>Cannot message yourself</h1><p>You are the seller of this listing.</p><a href="/browse">Browse listings</a></body></html>
        """)
    
    content = f"""
    <div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">Contact Seller</h1>
        <div class="bg-white shadow rounded-lg p-6">
            <div class="mb-6 p-4 bg-gray-50 rounded-lg">
                <p class="text-sm text-gray-500">Regarding:</p>
                <p class="text-lg font-semibold">{listing_title}</p>
                <p class="text-sm text-gray-500">Seller: {seller_email}</p>
            </div>
            <form action="/api/messages" method="POST">
                <input type="hidden" name="listing_id" value="{listing_id}">
                <input type="hidden" name="buyer_id" value="{buyer_id}">
                <input type="hidden" name="seller_id" value="{seller_id}">
                <div class="mb-6">
                    <label for="content" class="block text-sm font-medium text-gray-700 mb-2">Message</label>
                    <textarea name="content" id="content" rows="6" required class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="Hi, I'm interested in this item..."></textarea>
                </div>
                <button type="submit" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700">
                    Send Message
                </button>
            </form>
        </div>
    </div>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, "Contact Seller - Nova Exchange", navbar))


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
    
    existing_conv = get_conversation_by_listing_and_buyer(listing_id, buyer_id)
    
    if existing_conv:
        conversation_id = existing_conv.get("id")
    else:
        from api.messages import ConversationCreate
        conversation_data = ConversationCreate(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=seller_id
        )
        conversation = create_conv_func(conversation_data, access_token)
        if not conversation or not conversation.get("id"):
            return HTMLResponse("Failed to create conversation", status_code=500)
        conversation_id = conversation["id"]
    
    message_data = {
        "conversation_id": conversation_id,
        "sender_id": buyer_id,
        "content": content
    }
    create_msg_func(message_data, access_token)
    
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
    
    conversation = get_conversation_by_id(conversation_id, access_token)
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
    create_message_from_dict(message_data, access_token)
    
    return RedirectResponse(f"/messages?tab={active_tab}&chat={conversation_id}", status_code=303)


@app.post("/auth/logout")
async def logout(request: Request):
    from lib.supabase import logout_via_rest
    access_token = request.cookies.get("sb-access-token", "")
    
    if access_token:
        try:
            logout_via_rest(access_token)
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
    
    # Get user's access token from cookie for authenticated requests
    access_token = request.cookies.get("sb-access-token", "")
    
    # Ensure profile exists for this user (uses auth token if available)
    try:
        ensure_profile(user_id, access_token)
    except Exception as e:
        logger.error(f"Error ensuring profile: {e}")
    
    try:
        # Pass access_token to get profile with proper auth context
        profile = get_profile_by_user_id(user_id, access_token)
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        profile = None
    
    try:
        listings = get_listings_by_user(user_id)
    except Exception as e:
        logger.error(f"Error fetching listings: {e}")
        listings = []
    
    try:
        rating = get_average_rating(user_id)
    except Exception as e:
        logger.error(f"Error fetching rating: {e}")
        rating = {"average_rating": 0.0, "review_count": 0}
    
    # Use access_token for auth check (already have it)
    
    # Fetch user email from auth
    access_token = request.cookies.get("sb-access-token", "")
    user_email = ""
    current_user_id = ""
    if access_token:
        from lib.supabase import get_user_via_rest
        user_data = get_user_via_rest(access_token)
        if user_data:
            current_user_id = user_data.get("id", "")
            user_email = user_data.get("email", "")
    
    # Check if viewing own profile
    is_own_profile = current_user_id == user_id
    
    # Fetch reviews (not own profile only)
    reviews = []
    if not is_own_profile:
        try:
            from api.reviews import get_reviews_by_seller
            reviews = get_reviews_by_seller(user_id)
        except Exception as e:
            logger.error(f"Error fetching reviews: {e}")
    
    # Fetch conversations (own profile only)
    conversations = []
    if is_own_profile:
        try:
            conversations = get_conversations(user_id, access_token)
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
    
    # Fetch purchases (items user bought as buyer_id in transactions)
    purchases = []
    purchase_seller_review_status = {}  # Track which sellers user already reviewed
    if is_own_profile and access_token:
        try:
            from lib.supabase import rest_select_auth, rest_select
            purchases = rest_select_auth("transactions", access_token, filters={"buyer_id": f"eq.{user_id}"}, order="created_at.desc")
            
            # Get all reviews user has already submitted
            all_reviews = rest_select_auth("reviews", access_token, filters={"reviewer_id": f"eq.{user_id}"})
            reviewed_sellers = {r.get("seller_id") for r in all_reviews if r.get("seller_id")}
            
            # Enrich with listing data and seller info
            for purchase in purchases:
                listing_id = purchase.get("listing_id")
                seller_id = purchase.get("seller_id")
                if listing_id:
                    listing_data = rest_select("listings", filters={"id": f"eq.{listing_id}"})
                    if listing_data:
                        purchase["listing_title"] = listing_data[0].get("title")
                        purchase["listing_price"] = listing_data[0].get("price")
                        purchase["listing_image"] = listing_data[0].get("image_urls", [])[0] if listing_data[0].get("image_urls") else None
                # Store seller_id for rating button
                purchase["seller_id"] = seller_id
                # Check if already reviewed this seller
                purchase["already_reviewed"] = seller_id in reviewed_sellers
        except Exception as e:
            logger.error(f"Error fetching purchases: {e}")
    
    # Profile data
    name = (profile.get("name") or "") if profile else ""
    bio = (profile.get("bio") or "") if profile else ""
    phone = (profile.get("phone") or "") if profile else ""
    show_phone = profile.get("show_phone", False) if profile else False
    avatar_url = profile.get("avatar_url") if profile else None
    created_at = profile.get("created_at", "") if profile else ""
    join_date = ""
    if created_at:
        try:
            join_date = created_at[:7]  # YYYY-MM
        except:
            join_date = created_at
    
    is_editing = request.query_params.get("edit") == "1"
    review_error = request.query_params.get("error")
    
    # Check if current user already reviewed this seller
    already_reviewed = False
    can_review = False
    if current_user_id and not is_own_profile and current_user_id != user_id:
        try:
            from lib.supabase import rest_select_auth, rest_select
            # Check for valid transaction (user bought from this seller)
            transactions = rest_select_auth(
                "transactions",
                access_token,
                filters={"buyer_id": f"eq.{current_user_id}", "seller_id": f"eq.{user_id}"}
            )
            can_review = transactions and len(transactions) > 0
            
            # Check if already reviewed this seller
            if can_review:
                existing = rest_select_auth(
                    "reviews",
                    access_token,
                    filters={"reviewer_id": f"eq.{current_user_id}", "seller_id": f"eq.{user_id}"}
                )
                already_reviewed = existing and len(existing) > 0
        except Exception as e:
            logger.error(f"Error checking review eligibility: {e}")
    
    # Star rating display
    avg_rating_val = rating.get("average_rating", 0)
    review_count = rating.get("review_count", 0)
    
    # Listing cards
    emojis = ["📘", "🖥️", "🪑", "📱", "🎸", "🚲"]
    category_icons = {"Textbooks": "📚", "Electronics": "💻", "Furniture": "🪑", "Monitors": "🖥️", "Other": "📦"}
    condition_colors = {"New": "bg-green-100 text-green-800", "Like New": "bg-green-100 text-green-800", "Good": "bg-yellow-100 text-yellow-800", "Fair": "bg-gray-100 text-gray-800", "Poor": "bg-red-100 text-red-800"}
    
    listing_cards = ""
    for i, listing in enumerate(listings):
        emoji = category_icons.get(listing.get("category", ""), emojis[i % len(emojis)])
        title = listing.get("title", "Untitled")
        price = listing.get("price", 0)
        lid = listing.get("id", "")
        condition = listing.get("condition", "")
        image_urls = listing.get("image_urls", []) if listing.get("image_urls") else []
        image_url = image_urls[0] if image_urls else None
        
        condition_class = condition_colors.get(condition, "bg-gray-100 text-gray-800")
        
        listing_cards += f"""
        <a href="/listings/{lid}" class="block bg-white rounded-lg shadow-sm hover:shadow-md overflow-hidden">
            <div class="relative h-40 bg-gradient-to-br from-emerald-50 to-emerald-100 flex items-center justify-center">
                {f'<img src="{image_url}" alt="{title}" class="w-full h-full object-contain" loading="lazy" />' if image_url else f'<span class="text-5xl">{emoji}</span>'}
                <div class="absolute top-2 left-2">
                    <span class="{condition_class} text-xs px-2 py-0.5 rounded">{condition}</span>
                </div>
            </div>
            <div class="p-3">
                <h3 class="font-semibold text-sm text-gray-900 truncate">{title}</h3>
                <p class="text-xs text-gray-500">{listing.get('category', '')}</p>
            </div>
            <div class="px-3 pb-3">
                <span class="text-lg font-bold text-emerald-600">€{price}</span>
            </div>
        </a>"""
    
    # Purchases HTML (Buyer View)
    purchases_html = ""
    for purchase in purchases:
        listing_title = purchase.get("listing_title", "Unknown Item")
        listing_price = purchase.get("listing_price", 0)
        listing_image = purchase.get("listing_image")
        created = purchase.get("created_at", "")[:10] if purchase.get("created_at") else ""
        already_reviewed = purchase.get("already_reviewed", False)
        
        rate_button = ""
        if already_reviewed:
            rate_button = '<span class="block w-full text-xs text-gray-400 mt-1">Reviewed ✓</span>'
        else:
            rate_button = f'<button type="button" onclick="rateSellerFromPurchase(\'{purchase.get("seller_id", "")}\')" class="block w-full text-xs text-emerald-600 hover:underline mt-1">Rate Seller</button>'
        
        purchases_html += f"""
        <div class="block bg-white rounded-lg shadow-sm hover:shadow-md p-3 mb-2">
            <div class="flex items-center gap-3">
                <div class="h-12 w-12 rounded-lg bg-emerald-100 flex items-center justify-center overflow-hidden">
                    {f'<img src="{listing_image}" class="w-full h-full object-cover" loading="lazy" />' if listing_image else '<span class="text-2xl">📦</span>'}
                </div>
                <div class="flex-1">
                    <h3 class="font-semibold text-sm">{listing_title}</h3>
                    <p class="text-xs text-gray-500">Purchased: {created}</p>
                </div>
                <div>
                    <span class="text-lg font-bold text-emerald-600">€{listing_price}</span>
                    {rate_button}
                </div>
            </div>
        </div>"""
    
    # Reviews HTML
    reviews_html = ""
    for review in reviews:
        reviewer_name = review.get("reviewer_name", "Anonymous")
        rating_val = review.get("rating", 0)
        comment = review.get("comment", "")
        created = review.get("created_at", "")[:10] if review.get("created_at") else ""
        
        star_html = ""
        for i in range(1, 6):
            cls = "text-yellow-400" if i <= rating_val else "text-gray-300"
            star_html += f"<span class='{cls}'>★</span>"
        
        reviews_html += f"""
        <div class="border-b border-gray-200 pb-4 last:border-0">
            <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2">
                    <div class="h-7 w-7 rounded-full bg-emerald-100 flex items-center justify-center">
                        <span class="text-emerald-600 text-sm">{reviewer_name[0].upper()}</span>
                    </div>
                    <span class="text-sm font-medium">{reviewer_name}</span>
                </div>
                <span class="text-xs text-gray-500">{created}</span>
            </div>
            <div class="ml-9">
                <div class="text-yellow-400">{star_html}</div>
                {f'<p class="text-sm text-gray-500 mt-1">{comment}</p>' if comment else ''}
            </div>
        </div>"""
    
    # Conversions HTML - using simplified card
    def make_conv_card(conv):
        other_name = conv.get("other_user_name", "User")
        other_user_id = conv.get("other_user_id", "")
        last_msg = conv.get("last_message", "No messages yet")
        conv_id = conv.get("id", "")
        unread = conv.get("unread_count", 0)
        return f'''
        <a href="/messages" class="block bg-white rounded-lg shadow-sm hover:shadow-md p-3 mb-2">
            <div class="flex items-center gap-3">
                <div class="h-9 w-9 rounded-full bg-emerald-100 flex items-center justify-center">
                    <span class="text-emerald-600">{other_name[0].upper() if other_name else "?"}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between">
                        <span class="text-sm font-semibold truncate">{other_name}</span>
                        {f'<span class="bg-emerald-600 text-white text-xs px-1.5 py-0 rounded">{unread}</span>' if unread > 0 else ''}
                    </div>
                    <p class="text-xs text-gray-500 truncate">{last_msg}</p>
                </div>
            </div>
        </a>'''
    
    conversations_html = "".join(make_conv_card(conv) for conv in conversations[:5])
    
    # Reviews section - always show reviews (read-only for other users)
    # Rating only from My Purchases, not from seller's profile
    review_form = ""
    reviews_section = ""
    
    # Avatar and display name (needed by edit form)
    display_name = name or "Anonymous"
    if avatar_url:
        avatar_display = f'<img src="{avatar_url}" alt="{display_name}" class="h-20 w-20 rounded-full object-cover" />'
    else:
        avatar_display = f'<span class="text-3xl font-bold text-white">{display_name[0].upper() if display_name else "U"}</span>'
    
    # Edit form
    edit_form = ""
    if is_own_profile and is_editing:
        edit_form = f"""
        <form action="/profile/edit" method="POST" enctype="multipart/form-data" class="space-y-3">
            <div class="flex flex-col items-center mb-4">
                <div class="h-20 w-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center overflow-hidden mb-2">
                    {avatar_display}
                </div>
                <label class="block text-xs text-gray-500 mb-1">Profile Photo</label>
                <input type="file" name="avatar" accept="image/*" class="text-sm" />
            </div>
            <div>
                <label class="block text-xs text-gray-500 mb-1">Name</label>
                <input type="text" name="name" value="{name or ''}" class="w-full px-3 py-2 border border-gray-300 rounded-md" />
            </div>
            <div>
                <label class="block text-xs text-gray-500 mb-1">Bio</label>
                <textarea name="bio" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-md">{bio}</textarea>
            </div>
            <div>
                <label class="block text-xs text-gray-500 mb-1">Phone number</label>
                <input type="tel" name="phone" value="{phone or ''}" placeholder="+351 912 345 678" class="w-full px-3 py-2 border border-gray-300 rounded-md" />
            </div>
            <div class="flex items-center gap-2">
                <input type="checkbox" name="show_phone" {'checked' if show_phone else ''} class="h-4 w-4" />
                <label class="text-xs">Allow buyers to see my phone number on my listings</label>
            </div>
            <div class="flex gap-2">
                <button type="submit" class="bg-emerald-600 text-white px-4 py-2 rounded-md text-sm">Save</button>
                <a href="/profile/{user_id}" class="px-4 py-2 text-gray-500 text-sm">Cancel</a>
            </div>
        </form>"""
    
    # Display content
    display_name = name or "Anonymous"
    if is_own_profile:
        edit_button = f'<a href="/profile/{user_id}?edit=1" class="text-gray-500 text-sm hover:text-emerald-600">Edit</a>'
    else:
        edit_button = ""
    
    # Rating display
    rating_display = ""
    if review_count > 0:
        star_html = ""
        for i in range(1, 6):
            cls = "text-yellow-400" if i <= round(avg_rating_val) else "text-gray-300"
            star_html += f"<span class='{cls}'>★</span>"
        rating_display = f'<div class="flex items-center gap-1.5">{star_html}<span class="text-sm text-gray-500">{avg_rating_val} ({review_count} reviews)</span></div>'
    
    # Profile header
    if is_editing:
        profile_info = edit_form
    else:
        profile_info = f"""
        <div>
            <div class="flex items-center gap-3 flex-wrap">
                <h1 class="text-2xl font-bold">{display_name}</h1>
                {edit_button}
            </div>
            {f'<p class="text-sm text-gray-500 mt-1">{bio}</p>' if bio else ''}
            <div class="flex items-center gap-4 mt-3 flex-wrap">
                <div class="flex items-center gap-1.5 text-sm text-gray-500">
                    <span>📅</span>Joined {join_date}
                </div>
                {rating_display}
                <div class="flex items-center gap-1.5 text-sm text-gray-500">
                    <span>📦</span>{len(listings)} listing{'' if len(listings) == 1 else 's'}
                </div>
            </div>
        </div>"""
    
    content = f"""
    <div class="min-h-screen bg-gradient-to-b from-emerald-50/50 to-white">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <!-- Profile Header -->
            <div class="bg-white rounded-lg shadow-lg border border-gray-100 mb-8">
                <div class="p-6">
                    <div class="flex flex-col sm:flex-row items-start gap-6">
                        <!-- Avatar -->
                        <div class="relative group shrink-0">
                            <div class="h-20 w-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center overflow-hidden">
                                {avatar_display}
                            </div>
                        </div>
                        <!-- Info -->
                        <div class="flex-1 min-w-0">
                            {profile_info}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Listings Grid -->
            <div class="mb-8">
                <h2 class="text-xl font-bold mb-4">Listings</h2>
                {f'<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{listing_cards}</div>' if listing_cards else '<div class="bg-white rounded-lg shadow border border-gray-100 p-12 text-center"><p class="text-gray-500">No listings yet.</p></div>'}
            </div>
            
            <!-- Messages (own profile only) -->
            {f'''
            <div class="mb-8">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-bold">Messages</h2>
                    <a href="/messages" class="text-sm text-emerald-600 hover:underline">View all</a>
                </div>
                {f'<div class="space-y-2">{conversations_html}</div>' if conversations_html else '<div class="bg-white rounded-lg shadow border border-gray-100 p-8 text-center"><p class="text-gray-500">No messages yet</p></div>'}
            </div>
            ''' if is_own_profile else ''}
            
            <!-- Purchases (own profile only - Buyer View) -->
            {f'''
            <div class="mb-8">
                <h2 class="text-xl font-bold mb-4">My Purchases</h2>
                {f'<div class="space-y-2">{purchases_html}</div>' if purchases_html else '<div class="bg-white rounded-lg shadow border border-gray-100 p-8 text-center"><p class="text-gray-500">No purchases yet</p></div>'}
            </div>
            ''' if is_own_profile else ''}
            
            <!-- Reviews -->
            <div class="bg-white rounded-lg shadow-lg border border-gray-100">
                <div class="p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-xl font-bold">Reviews</h2>
                        {rating_display if review_count > 0 else ''}
                    </div>
                    {review_form}
                    {f'<div class="space-y-4">{reviews_html}</div>' if reviews_html else '<p class="text-sm text-gray-500 text-center py-6">No reviews yet.</p>'}
                </div>
            </div>
        </div>
    </div>
    
    <!-- Rate Seller Modal -->
    <div id="rate-modal" class="fixed inset-0 bg-black/50 z-50 hidden flex items-center justify-center">
        <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Rate Seller</h3>
                <button type="button" onclick="closeRateModal()" class="text-gray-500 text-2xl">&times;</button>
            </div>
            <p class="text-gray-600 mb-4">How would you rate this seller?</p>
            <div class="flex gap-2 mb-4 justify-center" id="rating-stars">
                <button type="button" onclick="setRating(1)" class="text-3xl hover:scale-110">★</button>
                <button type="button" onclick="setRating(2)" class="text-3xl hover:scale-110">★</button>
                <button type="button" onclick="setRating(3)" class="text-3xl hover:scale-110">★</button>
                <button type="button" onclick="setRating(4)" class="text-3xl hover:scale-110">★</button>
                <button type="button" onclick="setRating(5)" class="text-3xl hover:scale-110">★</button>
            </div>
            <input type="hidden" id="rating-value" value="0">
            <input type="hidden" id="rating-seller-id" value="">
            <textarea id="rating-comment" placeholder="Optional comment..." class="w-full px-3 py-2 border border-gray-300 rounded-md mb-4" rows="3"></textarea>
            <button type="button" onclick="submitRating()" class="w-full bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
                Submit Review
            </button>
            <p id="rate-error" class="text-red-500 text-sm mt-2 hidden"></p>
        </div>
    </div>
    
<script>
    var currentRating = 0;
    
    window.rateSellerFromPurchase = function(sellerId) {{
        document.getElementById("rating-seller-id").value = sellerId;
        currentRating = 0;
        document.getElementById("rating-value").value = "0";
        document.getElementById("rating-comment").value = "";
        updateStarDisplay();
        document.getElementById("rate-modal").classList.remove("hidden");
    }};
    
    function closeRateModal() {{
        document.getElementById("rate-modal").classList.add("hidden");
    }}
    
    function setRating(rating) {{
        currentRating = rating;
        document.getElementById("rating-value").value = rating;
        updateStarDisplay();
    }}
    
    function updateStarDisplay() {{
        var stars = document.querySelectorAll("#rating-stars button");
        stars.forEach(function(star, idx) {{
            star.className = idx < currentRating ? "text-3xl text-yellow-400" : "text-3xl text-gray-300";
        }});
    }}
    
    async function submitRating() {{
        var rating = document.getElementById("rating-value").value;
        var sellerId = document.getElementById("rating-seller-id").value;
        var comment = document.getElementById("rating-comment").value;
        
        if (!rating || rating === "0") {{
            alert("Please select a rating");
            return;
        }}
        
        var formData = new FormData();
        formData.append("seller_id", sellerId);
        formData.append("rating", rating);
        if (comment) formData.append("comment", comment);
        
        try {{
            var response = await fetch("/reviews", {{
                method: "POST",
                body: formData
            }});
            
            if (response.ok) {{
                window.location.reload();
            }} else {{
                var errorEl = document.getElementById("rate-error");
                errorEl.textContent = "Error submitting review";
                errorEl.classList.remove("hidden");
            }}
        }} catch (err) {{
            var errorEl = document.getElementById("rate-error");
            errorEl.textContent = "Error: " + err.message;
            errorEl.classList.remove("hidden");
        }}
    }}
    </script>
    """
    navbar = await get_navbar(request)
    return HTMLResponse(render_page(content, f"{display_name} - Nova Exchange", navbar))


@app.post("/profile/edit")
async def edit_profile(request: Request, avatar: UploadFile = File(None)):
    from lib.supabase import rest_update
    from api.profiles import update_profile
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return RedirectResponse("/auth/login")
    
    # Get current user
    from lib.supabase import get_user_via_rest
    user_data = get_user_via_rest(access_token)
    print(f"DEBUG: user_data = {user_data}")
    if not user_data:
        return RedirectResponse("/auth/login")
    
    user_id = user_data.get("id", "")
    print(f"DEBUG: user_id = {user_id}")
    if not user_id:
        return RedirectResponse("/auth/login")
    
    # Parse form data
    form = await request.form()
    name = form.get("name", "")
    bio = form.get("bio", "")
    phone = form.get("phone", "")
    show_phone = form.get("show_phone") == "on"
    
    print(f"DEBUG: name={name}, bio={bio}, phone={phone}, show_phone={show_phone}")
    
    # Handle avatar upload
    avatar_url = None
    try:
        if avatar and avatar.filename:
            contents = await avatar.read()
            if contents:
                from lib.supabase import upload_image
                file_name = avatar.filename or "avatar.jpg"
                avatar_url = upload_image(contents, file_name, bucket="avatars", access_token=access_token)
                print(f"DEBUG: avatar uploaded: {avatar_url}")
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
    
    print(f"DEBUG: update_data = {update_data}")
    
    # Update profile via REST API (authenticated)
    try:
        from lib.supabase import rest_update_auth
        result = rest_update_auth("profiles", access_token, update_data, {"user_id": user_id})
        print(f"DEBUG: rest_update result = {result}")
    except Exception as e:
        print(f"Profile update error: {e}")
    
    return RedirectResponse(f"/profile/{user_id}", status_code=302)


@app.post("/reviews")
async def submit_review(request: Request):
    from lib.supabase import rest_insert, rest_select_auth
    
    access_token = request.cookies.get("sb-access-token", "")
    if not access_token:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Get current user
    from lib.supabase import get_user_via_rest
    user_data = get_user_via_rest(access_token)
    if not user_data:
        return RedirectResponse("/auth/login", status_code=303)
    
    current_user_id = user_data.get("id", "")
    user_email = user_data.get("email", "")
    
    if not current_user_id:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Parse form data
    form = await request.form()
    seller_id = form.get("seller_id", "")
    rating = form.get("rating", "0")
    comment = form.get("comment", "")
    
    try:
        rating_int = int(rating)
    except:
        rating_int = 0
    
    if not seller_id or rating_int == 0:
        return RedirectResponse(f"/profile/{seller_id}", status_code=303)
    
    # Can't review yourself
    if seller_id == current_user_id:
        return RedirectResponse(f"/profile/{seller_id}", status_code=303)
    
    # Check if user has a valid transaction with this seller (using authenticated query)
    transactions = rest_select_auth(
        "transactions",
        access_token,
        filters={"buyer_id": f"eq.{current_user_id}", "seller_id": f"eq.{seller_id}"}
    )
    if not transactions or len(transactions) == 0:
        # User didn't buy from this seller - cannot review
        return RedirectResponse(f"/profile/{seller_id}?error=not_a_buyer", status_code=303)
    
    # Check if already reviewed this seller (using authenticated query)
    existing_reviews = rest_select_auth(
        "reviews",
        access_token,
        filters={"reviewer_id": f"eq.{current_user_id}", "seller_id": f"eq.{seller_id}"}
    )
    if existing_reviews and len(existing_reviews) > 0:
        # Already reviewed - redirect back with error
        return RedirectResponse(f"/profile/{seller_id}?error=already_reviewed", status_code=303)
    
    try:
        from lib.supabase import rest_insert_auth
        rest_insert_auth("reviews", access_token, {
            "reviewer_id": current_user_id,
            "seller_id": seller_id,
            "rating": rating_int,
            "comment": comment or None
        })
    except Exception as e:
        print(f"Review submit error: {e}")
    
    return RedirectResponse(f"/profile/{seller_id}", status_code=303)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "Nova Exchange"}