# Reusable UI Components
# Extracted from main.py to reduce repetition

emojis = ["📘", "🖥️", "🪑", "📱", "🎸", "🚲"]

def listing_card(listing, emoji=None, index=0) -> str:
    """Generate listing card HTML - consolidated from all locations"""
    if not listing:
        return ""

    title = listing.get('title', 'Untitled')
    price = listing.get('price', 0)
    condition = listing.get('condition', 'N/A')
    category = listing.get('category', 'Other')
    listing_id = listing.get('id', '')

    image_urls = listing.get('image_urls') or []
    image_url = image_urls[0] if isinstance(image_urls, list) and image_urls else None

    if emoji is None:
        category_icons = {"Textbooks": "📚", "Electronics": "💻", "Furniture": "🪑", "Monitors": "🖥️", "Other": "📦"}
        emoji = category_icons.get(category, emojis[index % len(emojis)])

    image_html = f'<img src="{image_url}" class="w-full h-48 object-cover rounded-t-lg" alt="{title}">' if image_url else f'<div class="text-4xl mb-2 p-4 pb-0">{emoji}</div>'

    return f'''
    <a href="/listings/{listing_id}" class="block bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden">
        {image_html}
        <div class="p-4">
            <h3 class="text-lg font-semibold text-gray-900 truncate">{title}</h3>
            <p class="text-emerald-600 font-bold text-xl mt-1">€{price}</p>
            <div class="flex items-center mt-2 text-sm text-gray-500">
                <span class="bg-gray-100 px-2 py-1 rounded text-xs">{condition}</span>
                <span class="ml-2 text-xs">{category}</span>
            </div>
        </div>
    </a>'''


def conversation_card(conv, is_selected=False, active_tab="buying") -> str:
    """Generate conversation card HTML - consolidated"""
    if not conv:
        return ""
    
    conv_id = conv.get("id", "")
    avatar_url = conv.get("other_user_avatar_url") or ""
    name = conv.get("other_user_name", "User")
    listing_title = conv.get("listing_title", "Listing")
    last_msg = conv.get("last_message", "")
    unread = conv.get("unread_count", 0)
    thumb = conv.get("listing_thumbnail")
    
    # Handle avatar
    if avatar_url:
        avatar_html = f'<img src="{avatar_url}" class="w-12 h-12 rounded-full object-cover bg-gray-200">'
    else:
        avatar_html = f'<div class="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 font-semibold">{name[0].upper() if name else "?"}</div>'
    
    # Handle thumbnail
    thumb_html = f'<img src="{thumb}" class="w-12 h-12 rounded object-cover ml-2 flex-shrink-0">' if thumb else ''
    
    # Selected state
    selected_class = "bg-gray-100" if is_selected else "hover:bg-gray-50"
    
    unread_badge = f'<span class="w-2 h-2 bg-emerald-500 rounded-full flex-shrink-0"></span>' if unread > 0 else ''
    
    return f'''
    <a href="?tab={active_tab}&chat={conv_id}" class="flex items-center p-3 border-b {selected_class} transition-colors">
        {avatar_html}
        <div class="flex-1 min-w-0 ml-3">
            <div class="flex justify-between items-center">
                <span class="font-medium text-gray-900 truncate">{name}</span>
                {unread_badge}
            </div>
            <p class="text-xs text-gray-500 truncate">{listing_title}</p>
            <p class="text-sm text-gray-600 truncate">{last_msg or "No messages yet"}</p>
        </div>
        {thumb_html}
    </a>'''


def message_bubble(content, created_at, is_mine=True) -> str:
    """Generate message bubble HTML"""
    msg_class = "ml-auto bg-emerald-100" if is_mine else "mr-auto bg-white"
    align = "justify-end" if is_mine else "justify-start"
    
    return f'''
    <div class="flex {align} mb-3">
        <div class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg {msg_class} shadow-sm">
            <p class="text-gray-800">{content}</p>
            <p class="text-xs text-gray-400 mt-1 text-right">{created_at}</p>
        </div>
    </div>'''


def empty_state(title, message, icon="📭", action_link=None, action_text=None) -> str:
    """Generic empty state component"""
    action_html = ""
    if action_link and action_text:
        action_html = f'''
        <a href="{action_link}" class="mt-4 inline-block bg-emerald-600 text-white px-4 py-2 rounded-md hover:bg-emerald-700">
            {action_text}
        </a>'''
    
    return f'''
    <div class="text-center py-12">
        <div class="text-6xl mb-4">{icon}</div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
        <p class="text-gray-500 mb-4">{message}</p>
        {action_html}
    </div>'''


def loading_spinner(size="md") -> str:
    """Loading spinner component"""
    if size == "sm":
        size_class = "h-4 w-4"
    elif size == "lg":
        size_class = "h-12 w-12"
    else:
        size_class = "h-8 w-8"
    
    animate_class = "animate-spin" if size != "sm" else ""
    
    return f'''
    <div class="flex items-center justify-center">
        <div class="{size_class} border-2 border-emerald-200 border-t-emerald-600 rounded-full {animate_class}"></div>
    </div>'''


def toast_message(message, type="success") -> str:
    """Toast notification component"""
    bg_class = "bg-emerald-500" if type == "success" else "bg-red-500"
    
    return f'''
    <div class="fixed bottom-4 right-4 {bg_class} text-white px-4 py-2 rounded-lg shadow-lg z-50">
        {message}
    </div>'''


def delete_confirmation_modal(item_type="item", onConfirmJS="deleteItem()") -> str:
    """Delete confirmation dialog"""
    return f'''
    <div id="delete-modal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
        <div class="bg-white rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 class="text-lg font-semibold mb-2">Delete {item_type}?</h3>
            <p class="text-gray-600 mb-4">This action cannot be undone.</p>
            <div class="flex gap-2">
                <button onclick="{onConfirmJS}" class="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                    Delete
                </button>
                <button onclick="document.getElementById('delete-modal').classList.add('hidden')" class="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
                    Cancel
                </button>
            </div>
        </div>
    </div>'''


def back_to_top_button() -> str:
    """Back to top button"""
    return '''
    <button onclick="window.scrollTo({top:0,behavior:'smooth'})" 
        class="fixed bottom-4 right-4 bg-emerald-600 text-white w-10 h-10 rounded-full shadow-lg hover:bg-emerald-700 flex items-center justify-center text-xl z-40">
        ↑
    </button>'''


def star_rating(rating, size="md") -> str:
    """Star rating display"""
    if size == "lg":
        size_class = "h-5 w-5"
    else:
        size_class = "h-4 w-4"
    
    stars = ""
    for i in range(1, 6):
        filled = i <= rating
        color = "text-yellow-400" if filled else "text-gray-300"
        stars += f'<span class="{size_class} {color}">★</span>'
    
    return f'<div class="flex gap-0.5">{stars}</div>'


def form_select(name, label, options, selected=None, required=False) -> str:
    """Reusable select dropdown"""
    required_attr = "required" if required else ""
    
    options_html = ""
    for value, text in options:
        selected_attr = "selected" if value == selected else ""
        options_html += f'<option value="{value}" {selected_attr}>{text}</option>'
    
    return f'''
    <div>
        <label for="{name}" class="block text-sm font-medium text-gray-700 mb-1">{label}</label>
        <select name="{name}" id="{name}" class="w-full px-3 py-2 border border-gray-300 rounded-md" {required_attr}>
            {options_html}
        </select>
    </div>'''


def form_input(name, label, type="text", value="", placeholder="", required=False) -> str:
    """Reusable text input"""
    required_attr = "required" if required else ""
    
    return f'''
    <div>
        <label for="{name}" class="block text-sm font-medium text-gray-700 mb-1">{label}</label>
        <input type="{type}" name="{name}" id="{name}" value="{value}" placeholder="{placeholder}" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md" {required_attr}>
    </div>'''