"""
UI Design System - Professional styling constants and helpers
"""

# ============================================================================
# EMOJI SYSTEM - Consistent visual language
# ============================================================================

EMOJI = {
    # Actions
    "add": "➕",
    "remove": "➖",
    "edit": "✏️",
    "delete": "🗑️",
    "save": "💾",
    "send": "📤",
    "receive": "📥",
    "search": "🔍",
    "filter": "🔽",
    "refresh": "🔄",
    "settings": "⚙️",
    
    # Status
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "pending": "⏳",
    "processing": "⚡",
    "completed": "🎉",
    
    # Money & Business
    "money": "💰",
    "dollar": "💵",
    "coin": "🪙",
    "chart_up": "📈",
    "chart_down": "📉",
    "profit": "💸",
    "payment": "💳",
    "wallet": "👛",
    
    # Communication
    "message": "💬",
    "notification": "🔔",
    "email": "📧",
    "phone": "📱",
    "megaphone": "📣",
    "announcement": "📢",
    
    # Content
    "image": "🖼️",
    "video": "🎥",
    "document": "📄",
    "link": "🔗",
    "star": "⭐",
    "fire": "🔥",
    "rocket": "🚀",
    
    # Users & Channels
    "user": "👤",
    "users": "👥",
    "channel": "📺",
    "broadcast": "📡",
    "group": "👨‍👩‍👧‍👦",
    "owner": "👑",
    "advertiser": "💼",
    
    # Navigation
    "home": "🏠",
    "back": "◀️",
    "forward": "▶️",
    "up": "⬆️",
    "down": "⬇️",
    "menu": "📋",
    "dashboard": "📊",
    
    # Time
    "clock": "🕐",
    "calendar": "📅",
    "timer": "⏱️",
    "history": "📜",
    
    # Quality
    "premium": "💎",
    "verified": "✔️",
    "badge": "🏆",
    "medal": "🥇",
    "ribbon": "🎀",
    
    # Actions - Specific
    "browse": "🔍",
    "shop": "🛍️",
    "cart": "🛒",
    "order": "📦",
    "delivery": "🚚",
    "review": "📝",
    "approve": "👍",
    "reject": "👎",
    
    # Misc
    "light": "💡",
    "target": "🎯",
    "gift": "🎁",
    "celebrate": "🎊",
    "party": "🎉",
}


# ============================================================================
# VISUAL SEPARATORS
# ============================================================================

def create_separator(style="light"):
    """Create visual separator lines"""
    separators = {
        "light": "─" * 30,
        "medium": "━" * 30,
        "heavy": "═" * 30,
        "dots": "· " * 15,
        "stars": "✦ " * 10,
    }
    return separators.get(style, separators["light"])


def create_box_header(title, emoji=""):
    """Create a boxed header"""
    title_text = f"{emoji} {title}" if emoji else title
    line = "━" * (len(title_text) + 4)
    return f"┏{line}┓\n┃  {title_text}  ┃\n┗{line}┛"


def create_section_header(title, emoji=""):
    """Create a section header"""
    return f"\n{'═' * 40}\n{emoji} {title}\n{'═' * 40}\n"


# ============================================================================
# TEXT FORMATTING HELPERS
# ============================================================================

def format_price(amount, currency="USD"):
    """Format price consistently"""
    return f"{EMOJI['dollar']} {amount:.2f} {currency}"


def format_status(status):
    """Format order status with emoji"""
    status_map = {
        "pending_payment": f"{EMOJI['pending']} Pending Payment",
        "paid": f"{EMOJI['success']} Paid",
        "creative_submitted": f"{EMOJI['processing']} Under Review",
        "posted": f"{EMOJI['completed']} Posted",
        "completed": f"{EMOJI['badge']} Completed",
        "cancelled": f"{EMOJI['error']} Cancelled",
    }
    return status_map.get(status, status)


def format_count(count, label):
    """Format count with label"""
    return f"{count} {label}{'s' if count != 1 else ''}"


def create_info_line(label, value, emoji=""):
    """Create formatted info line"""
    prefix = f"{emoji} " if emoji else "  "
    return f"{prefix}{label}: {value}"


def create_progress_bar(current, total, width=10):
    """Create a simple progress bar"""
    filled = int((current / total) * width)
    bar = "█" * filled + "░" * (width - filled)
    percentage = int((current / total) * 100)
    return f"{bar} {percentage}%"


# ============================================================================
# CARD LAYOUTS
# ============================================================================

def create_channel_card(channel_data):
    """Create a beautiful channel card"""
    name = channel_data.get('channel_title', 'Unknown')
    subscribers = channel_data.get('subscribers', 0)
    avg_views = channel_data.get('avg_views', 0)
    pricing = channel_data.get('pricing', {})
    
    card = f"{EMOJI['channel']} {name}\n"
    card += f"{create_separator('dots')}\n"
    card += f"{EMOJI['users']} {subscribers:,} subscribers\n"
    card += f"{EMOJI['chart_up']} {avg_views:,} avg views\n"
    card += f"\n{EMOJI['money']} Pricing:\n"
    
    for ad_type, price in pricing.items():
        card += f"  • {ad_type.capitalize()}: {price} USD\n"
    
    return card


def create_order_card(order_data):
    """Create a beautiful order card"""
    order_id = order_data.get('id')
    ad_type = order_data.get('ad_type', '').capitalize()
    price = order_data.get('price', 0)
    status = order_data.get('status', '')
    
    card = f"{EMOJI['order']} Order #{order_id}\n"
    card += f"{create_separator('dots')}\n"
    card += f"  Type: {ad_type}\n"
    card += f"  {format_price(price)}\n"
    card += f"  {format_status(status)}\n"
    
    return card


def create_earnings_card(earnings_data):
    """Create earnings summary card"""
    total = earnings_data.get('total', 0)
    completed = earnings_data.get('completed', 0)
    pending = earnings_data.get('pending', 0)
    
    card = f"{EMOJI['money']} Total Earnings\n"
    card += f"{create_separator('stars')}\n"
    card += f"{EMOJI['dollar']} {total:.2f} USD\n"
    card += f"{EMOJI['success']} {completed} completed\n"
    card += f"{EMOJI['pending']} {pending} pending\n"
    
    return card


# ============================================================================
# BUTTON STYLES
# ============================================================================

def format_button_text(text, icon="", style="default"):
    """Format button text with icons"""
    styles = {
        "primary": f"{icon} {text} {icon}",
        "success": f"{EMOJI['success']} {text}",
        "danger": f"{EMOJI['error']} {text}",
        "default": f"{icon} {text}" if icon else text,
    }
    return styles.get(style, styles["default"])


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

def create_welcome_message(user_name):
    """Create welcome message"""
    message = f"{EMOJI['party']} Welcome to AdMarket!\n\n"
    message += f"Hello {user_name}! {EMOJI['wave']}\n\n"
    message += f"{EMOJI['rocket']} Your gateway to Telegram advertising\n"
    message += f"{EMOJI['chart_up']} Connect channels with advertisers\n"
    message += f"{EMOJI['money']} Earn money or grow your brand\n\n"
    message += f"{create_separator('light')}\n"
    message += f"{EMOJI['info']} Choose your role below to get started"
    return message


def create_success_message(title, details=""):
    """Create success message"""
    message = f"{EMOJI['party']} {title}\n\n"
    if details:
        message += f"{details}\n\n"
    message += f"{EMOJI['success']} Operation completed successfully!"
    return message


def create_error_message(title, details=""):
    """Create error message"""
    message = f"{EMOJI['error']} {title}\n\n"
    if details:
        message += f"{details}\n\n"
    message += f"{EMOJI['warning']} Please try again or contact support"
    return message
