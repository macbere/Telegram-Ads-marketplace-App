"""
Telegram Bot Handlers - Complete with Purchase Flow
Handles all bot interactions including purchases, payments, and order management
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = Router()

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:10000")


# ============================================================================
# FSM STATES
# ============================================================================

class ChannelRegistration(StatesGroup):
    """States for channel registration flow"""
    waiting_for_forward = State()
    waiting_for_pricing = State()


class PurchaseFlow(StatesGroup):
    """States for ad purchase flow"""
    selecting_ad_type = State()
    confirming_purchase = State()
    selecting_payment = State()
    submitting_creative = State()
    waiting_for_creative_text = State()
    waiting_for_creative_media = State()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def api_request(method: str, endpoint: str, **kwargs):
    """Make API request to FastAPI backend"""
    url = f"{API_BASE_URL}{endpoint}"
    
    logger.info(f"🔗 API {method} {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.info("✅ HTTP session created")
            async with session.request(method, url, **kwargs) as response:
                logger.info(f"📥 Response: {response.status}")
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API Error {response.status}: {error_text}")
                    return {"error": error_text, "status": response.status}
    except Exception as e:
        logger.error(f"❌ Request failed: {e}")
        return {"error": str(e)}


def create_main_menu_keyboard(is_owner=False, is_advertiser=False):
    """Create main menu keyboard based on user roles"""
    keyboard = []
    
    if not is_owner and not is_advertiser:
        # First-time user - ask for role
        keyboard = [
            [InlineKeyboardButton(text="📢 I'm a Channel Owner", callback_data="role_channel_owner")],
            [InlineKeyboardButton(text="🎯 I'm an Advertiser", callback_data="role_advertiser")]
        ]
    else:
        # Existing user menu
        if is_owner:
            keyboard.append([InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")])
            keyboard.append([InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")])
        
        if is_advertiser:
            keyboard.append([InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")])
            keyboard.append([InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")])
        
        # Always show switch role option
        if is_owner and not is_advertiser:
            keyboard.append([InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")])
        elif is_advertiser and not is_owner:
            keyboard.append([InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    logger.info(f"👤 /start from user {message.from_user.id} (@{message.from_user.username})")
    
    # Clear any existing state
    await state.clear()
    
    # Register user in database
    result = await api_request(
        "POST",
        "/users/",
        params={
            "telegram_id": message.from_user.id,
            "username": message.from_user.username or "",
            "first_name": message.from_user.first_name or ""
        }
    )
    
    if "error" in result:
        await message.answer("❌ Failed to register user. Please try again later.")
        return
    
    logger.info(f"✅ User registered: {message.from_user.id}")
    
    # Create welcome message
    welcome_text = (
        f"👋 Welcome to Telegram Ads Marketplace!\n\n"
        f"Connect channel owners with advertisers for seamless ad placements.\n\n"
        f"👤 **Your Profile:**\n"
        f"Name: {message.from_user.first_name}\n"
        f"Username: @{message.from_user.username or 'Not set'}\n\n"
        f"How would you like to use the marketplace?"
    )
    
    # Get user roles
    is_owner = result.get("is_channel_owner", False)
    is_advertiser = result.get("is_advertiser", False)
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 **Telegram Ads Marketplace Bot**\n\n"
        "**For Channel Owners:**\n"
        "• Add your channel to the marketplace\n"
        "• Set your own pricing\n"
        "• Manage incoming orders\n"
        "• Track earnings\n\n"
        "**For Advertisers:**\n"
        "• Browse available channels\n"
        "• Purchase ad slots\n"
        "• Submit creative content\n"
        "• Track order status\n\n"
        "**Commands:**\n"
        "/start - Main menu\n"
        "/help - Show this help message\n"
        "/stats - View marketplace statistics"
    )
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command"""
    stats = await api_request("GET", "/stats")
    
    if "error" in stats:
        await message.answer("❌ Failed to fetch statistics.")
        return
    
    stats_text = (
        f"📊 **Marketplace Statistics**\n\n"
        f"👥 Total Users: {stats.get('total_users', 0)}\n"
        f"📢 Active Channels: {stats.get('total_channels', 0)}\n"
        f"💼 Total Deals: {stats.get('total_deals', 0)}\n"
        f"🔥 Active Deals: {stats.get('active_deals', 0)}"
    )
    
    await message.answer(stats_text, parse_mode="Markdown")


# ============================================================================
# ROLE SELECTION CALLBACKS
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    """Handle channel owner role selection"""
    logger.info(f"📞 Callback: role_channel_owner from user {callback.from_user.id}")
    
    # Update user role
    result = await api_request(
        "POST",
        "/users/",
        params={
            "telegram_id": callback.from_user.id,
            "username": callback.from_user.username or "",
            "first_name": callback.from_user.first_name or ""
        }
    )
    
    # Update is_channel_owner flag (would need API endpoint for this)
    # For now, just show the menu
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "📢 **Channel Owner Menu**\n\n"
        "List your channels and start earning from advertisers!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    """Handle advertiser role selection"""
    logger.info(f"📞 Callback: role_advertiser from user {callback.from_user.id}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "🎯 **Advertiser Menu**\n\n"
        "Find the perfect channels for your advertising campaigns!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================================
# CHANNEL MANAGEMENT
# ============================================================================

@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    """Start channel registration flow"""
    await callback.message.edit_text(
        "📢 **Add Your Channel**\n\n"
        "Please forward a message from your channel to register it.\n\n"
        "Make sure the bot is an admin in your channel!",
        parse_mode="Markdown"
    )
    await state.set_state(ChannelRegistration.waiting_for_forward)
    await callback.answer()


@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded message from channel"""
    if not message.forward_from_chat:
        await message.answer("❌ Please forward a message from your channel.")
        return
    
    if message.forward_from_chat.type != "channel":
        await message.answer("❌ This is not a channel. Please forward from a channel.")
        return
    
    # Store channel info
    await state.update_data(
        channel_id=message.forward_from_chat.id,
        channel_title=message.forward_from_chat.title,
        channel_username=message.forward_from_chat.username
    )
    
    await message.answer(
        f"✅ **Channel Detected:**\n\n"
        f"📢 {message.forward_from_chat.title}\n"
        f"🔗 @{message.forward_from_chat.username or 'Private Channel'}\n\n"
        f"💰 **Set Your Pricing**\n\n"
        f"Please send your prices in this format:\n"
        f"`Post: 100\nStory: 50\nRepost: 25`\n\n"
        f"(Prices in USD)",
        parse_mode="Markdown"
    )
    
    await state.set_state(ChannelRegistration.waiting_for_pricing)


@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    """Process channel pricing input"""
    try:
        # Parse pricing
        pricing = {}
        lines = message.text.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                parts = line.split(':')
                key = parts[0].strip().lower()
                value = float(parts[1].strip())
                
                if key in ['post', 'story', 'repost']:
                    pricing[key] = value
        
        if not pricing:
            await message.answer(
                "❌ Invalid format. Please use:\n"
                "`Post: 100\nStory: 50\nRepost: 25`",
                parse_mode="Markdown"
            )
            return
        
        # Get channel data from state
        data = await state.get_data()
        
        # Register channel via API
        result = await api_request(
            "POST",
            "/channels/",
            json={
                "owner_telegram_id": message.from_user.id,
                "telegram_channel_id": data["channel_id"],
                "channel_title": data["channel_title"],
                "channel_username": data["channel_username"],
                "pricing": pricing
            }
        )
        
        if "error" in result:
            if "already exists" in str(result["error"]).lower():
                await message.answer(
                    f"ℹ️ **Channel Already Listed**\n\n"
                    f"{data['channel_title']} is already in the marketplace!",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(f"❌ Failed to register channel: {result['error']}")
        else:
            pricing_text = "\n".join([f"{k.title()}: ${v}" for k, v in pricing.items()])
            await message.answer(
                f"🎉 **Channel Listed Successfully!**\n\n"
                f"📢 Channel: {data['channel_title']}\n"
                f"💰 Pricing:\n{pricing_text}\n\n"
                f"Your channel is now visible to advertisers!\n"
                f"Channel ID: #{result.get('id')}",
                parse_mode="Markdown"
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing pricing: {e}")
        await message.answer(
            "❌ Failed to process pricing. Please use the correct format:\n"
            "`Post: 100\nStory: 50\nRepost: 25`",
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """Show user's channels"""
    # This would need an API endpoint to fetch user's channels
    await callback.message.edit_text(
        "📊 **My Channels**\n\n"
        "This feature is coming soon!\n"
        "You'll be able to:\n"
        "• View all your listed channels\n"
        "• See earnings per channel\n"
        "• Manage pricing\n"
        "• View pending orders",
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================================
# BROWSE CHANNELS & PURCHASE FLOW
# ============================================================================

@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery, state: FSMContext):
    """Show available channels"""
    logger.info(f"📞 Callback: browse_channels from user {callback.from_user.id}")
    
    # Fetch channels from API
    channels = await api_request("GET", "/channels/")
    
    # Type checking - ensure we have a list
    if not isinstance(channels, list):
        if isinstance(channels, dict) and "error" in channels:
            await callback.message.edit_text(
                f"❌ Failed to load channels: {channels['error']}",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                "❌ Unexpected response from server.",
                parse_mode="Markdown"
            )
        await callback.answer()
        return
    
    if len(channels) == 0:
        await callback.message.edit_text(
            "📢 **No Channels Available**\n\n"
            "No channels are currently listed in the marketplace.\n"
            "Check back later!",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Display channels
    for channel in channels[:5]:  # Show first 5 channels
        pricing = channel.get("pricing", {})
        pricing_text = "\n".join([
            f"  • {k.title()}: ${v}"
            for k, v in pricing.items()
        ])
        
        channel_text = (
            f"📢 **{channel['channel_title']}**\n"
            f"🔗 @{channel.get('channel_username', 'Private')}\n"
            f"👥 Subscribers: {channel.get('subscribers', 0):,}\n"
            f"👀 Avg Views: {channel.get('avg_views', 0):,}\n\n"
            f"💰 **Pricing:**\n{pricing_text}"
        )
        
        # Create purchase buttons
        keyboard = []
        for ad_type, price in pricing.items():
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🛒 Buy {ad_type.title()} - ${price}",
                    callback_data=f"purchase:{channel['id']}:{ad_type}:{price}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
        
        await callback.message.answer(
            channel_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
    
    await callback.message.delete()
    await callback.answer("✅ Channels loaded!")


@router.callback_query(F.data.startswith("purchase:"))
async def callback_purchase(callback: CallbackQuery, state: FSMContext):
    """Handle purchase initiation"""
    logger.info(f"📞 Callback: purchase from user {callback.from_user.id}")
    
    # Parse callback data: purchase:channel_id:ad_type:price
    parts = callback.data.split(":")
    channel_id = int(parts[1])
    ad_type = parts[2]
    price = float(parts[3])
    
    # Store purchase info in state
    await state.update_data(
        channel_id=channel_id,
        ad_type=ad_type,
        price=price
    )
    
    # Get channel details
    channel = await api_request("GET", f"/channels/{channel_id}")
    
    if "error" in channel:
        await callback.message.edit_text(
            "❌ Failed to load channel details.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Show purchase confirmation
    confirm_text = (
        f"🛒 **Order Confirmation**\n\n"
        f"📢 Channel: {channel['channel_title']}\n"
        f"📝 Ad Type: {ad_type.title()}\n"
        f"💰 Price: ${price}\n\n"
        f"Confirm your purchase?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm & Pay", callback_data="confirm_purchase"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_purchase")
        ]
    ])
    
    await callback.message.edit_text(
        confirm_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseFlow.confirming_purchase)
    await callback.answer()


@router.callback_query(F.data == "confirm_purchase", StateFilter(PurchaseFlow.confirming_purchase))
async def callback_confirm_purchase(callback: CallbackQuery, state: FSMContext):
    """Handle purchase confirmation and payment"""
    logger.info(f"📞 Callback: confirm_purchase from user {callback.from_user.id}")
    
    data = await state.get_data()
    
    # Create order
    order_data = {
        "buyer_telegram_id": callback.from_user.id,
        "channel_id": data["channel_id"],
        "ad_type": data["ad_type"],
        "price": data["price"]
    }
    
    result = await api_request("POST", "/orders/", json=order_data)
    
    if "error" in result:
        await callback.message.edit_text(
            f"❌ Failed to create order: {result['error']}",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    order_id = result.get("id")
    
    # Store order ID
    await state.update_data(order_id=order_id)
    
    # Show payment options
    payment_text = (
        f"💳 **Payment Options**\n\n"
        f"Order ID: #{order_id}\n"
        f"Amount: ${data['price']}\n\n"
        f"Choose your payment method:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON Crypto", callback_data="pay_ton")],
        [InlineKeyboardButton(text="💳 Card Payment", callback_data="pay_card")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        payment_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseFlow.selecting_payment)
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"), StateFilter(PurchaseFlow.selecting_payment))
async def callback_payment_method(callback: CallbackQuery, state: FSMContext):
    """Handle payment method selection"""
    payment_method = callback.data.split("_")[1]  # ton or card
    
    data = await state.get_data()
    order_id = data.get("order_id")
    
    logger.info(f"📞 Payment method: {payment_method} for order {order_id}")
    
    # Update order with payment method
    await api_request(
        "PATCH",
        f"/orders/{order_id}",
        json={"payment_method": payment_method}
    )
    
    # Simulate payment (in production, integrate real payment gateway)
    payment_text = (
        f"💳 **Payment Processing**\n\n"
        f"Order ID: #{order_id}\n"
        f"Method: {payment_method.upper()}\n"
        f"Amount: ${data['price']}\n\n"
        f"⏳ Processing payment...\n\n"
        f"_In production, this would redirect to payment gateway._\n\n"
        f"For this demo, payment is automatically approved."
    )
    
    await callback.message.edit_text(
        payment_text,
        parse_mode="Markdown"
    )
    
    # Simulate payment success
    await api_request(
        "PATCH",
        f"/orders/{order_id}",
        json={
            "status": "paid",
            "paid_at": datetime.utcnow().isoformat(),
            "payment_transaction_id": f"TXN_{order_id}_{int(datetime.utcnow().timestamp())}"
        }
    )
    
    # Show success and request creative
    success_text = (
        f"✅ **Payment Successful!**\n\n"
        f"Order ID: #{order_id}\n"
        f"Status: Paid\n\n"
        f"📝 **Next Step: Submit Creative**\n\n"
        f"Please send your ad content:\n"
        f"1. Text/Caption for your ad\n"
        f"2. Media (image/video) if needed"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Submit Creative Now", callback_data="submit_creative")],
        [InlineKeyboardButton(text="⏭️ Submit Later", callback_data="my_orders")]
    ])
    
    await callback.message.edit_text(
        success_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(PurchaseFlow.submitting_creative)
    await callback.answer("✅ Payment processed!")


@router.callback_query(F.data == "submit_creative", StateFilter(PurchaseFlow.submitting_creative))
async def callback_submit_creative(callback: CallbackQuery, state: FSMContext):
    """Start creative submission"""
    await callback.message.edit_text(
        "📝 **Submit Your Ad Creative**\n\n"
        "Please send the text/caption for your ad.\n\n"
        "You can include emojis, links, and formatting.",
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseFlow.waiting_for_creative_text)
    await callback.answer()


@router.message(StateFilter(PurchaseFlow.waiting_for_creative_text))
async def process_creative_text(message: Message, state: FSMContext):
    """Process creative text"""
    data = await state.get_data()
    order_id = data.get("order_id")
    
    # Save creative text
    await api_request(
        "PATCH",
        f"/orders/{order_id}",
        json={"creative_content": message.text}
    )
    
    await state.update_data(creative_text=message.text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📷 Yes, add media", callback_data="add_media")],
        [InlineKeyboardButton(text="✅ No, submit as is", callback_data="finalize_creative")]
    ])
    
    await message.answer(
        "✅ **Text Saved!**\n\n"
        "Do you want to add media (image/video)?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "add_media", StateFilter(PurchaseFlow.waiting_for_creative_text))
async def callback_add_media(callback: CallbackQuery, state: FSMContext):
    """Request media upload"""
    await callback.message.edit_text(
        "📷 **Upload Media**\n\n"
        "Please send your image or video.",
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseFlow.waiting_for_creative_media)
    await callback.answer()


@router.message(StateFilter(PurchaseFlow.waiting_for_creative_media))
async def process_creative_media(message: Message, state: FSMContext):
    """Process creative media"""
    data = await state.get_data()
    order_id = data.get("order_id")
    
    # Get media file_id
    media_id = None
    if message.photo:
        media_id = message.photo[-1].file_id
    elif message.video:
        media_id = message.video.file_id
    
    if not media_id:
        await message.answer("❌ Please send a valid image or video.")
        return
    
    # Save media
    await api_request(
        "PATCH",
        f"/orders/{order_id}",
        json={
            "creative_media_id": media_id,
            "status": "processing"
        }
    )
    
    await message.answer(
        "✅ **Creative Submitted!**\n\n"
        f"Order ID: #{order_id}\n"
        f"Status: Processing\n\n"
        "The channel owner will review your creative and post it soon.\n"
        "You'll be notified when it's live!",
        parse_mode="Markdown"
    )
    
    await state.clear()


@router.callback_query(F.data == "finalize_creative")
async def callback_finalize_creative(callback: CallbackQuery, state: FSMContext):
    """Finalize creative without media"""
    data = await state.get_data()
    order_id = data.get("order_id")
    
    # Update order status
    await api_request(
        "PATCH",
        f"/orders/{order_id}",
        json={"status": "processing"}
    )
    
    await callback.message.edit_text(
        "✅ **Creative Submitted!**\n\n"
        f"Order ID: #{order_id}\n"
        f"Status: Processing\n\n"
        "The channel owner will review your creative and post it soon.\n"
        "You'll be notified when it's live!",
        parse_mode="Markdown"
    )
    
    await state.clear()
    await callback.answer("✅ Creative submitted!")


@router.callback_query(F.data == "cancel_purchase")
async def callback_cancel_purchase(callback: CallbackQuery, state: FSMContext):
    """Cancel purchase"""
    await callback.message.edit_text(
        "❌ Purchase cancelled.",
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()


# ============================================================================
# MY ORDERS
# ============================================================================

@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """Show user's orders"""
    logger.info(f"📞 Callback: my_orders from user {callback.from_user.id}")
    
    # Fetch user's orders
    orders = await api_request("GET", f"/orders/user/{callback.from_user.id}")
    
    if isinstance(orders, dict) and "error" in orders:
        await callback.message.edit_text(
            "❌ Failed to load orders.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    if not isinstance(orders, list) or len(orders) == 0:
        await callback.message.edit_text(
            "🛒 **My Orders**\n\n"
            "You haven't placed any orders yet.\n\n"
            "Browse channels to get started!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return
    
    # Display orders
    orders_text = "🛒 **My Orders**\n\n"
    
    for order in orders[:10]:  # Show last 10 orders
        status_emoji = {
            "pending_payment": "⏳",
            "paid": "✅",
            "processing": "🔄",
            "completed": "✅",
            "cancelled": "❌",
            "refunded": "💸"
        }.get(order["status"], "❓")
        
        orders_text += (
            f"{status_emoji} **Order #{order['id']}**\n"
            f"   Ad Type: {order['ad_type'].title()}\n"
            f"   Price: ${order['price']}\n"
            f"   Status: {order['status'].replace('_', ' ').title()}\n"
            f"   Date: {order['created_at'][:10]}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Browse More Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        orders_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================================
# MAIN MENU
# ============================================================================

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await state.clear()
    
    # Get user data
    result = await api_request(
        "GET",
        f"/users/{callback.from_user.id}"
    )
    
    is_owner = result.get("is_channel_owner", False)
    is_advertiser = result.get("is_advertiser", False)
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    
    await callback.message.edit_text(
        "🏠 **Main Menu**\n\n"
        "What would you like to do?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================================
# ROUTER SETUP
# ============================================================================

def setup_handlers(dp):
    """Register all handlers with the dispatcher"""
    dp.include_router(router)
    logger.info("✅ Router registered with dispatcher")
    logger.info("📝 Registered handlers:")
    logger.info("  - Commands: /start, /help, /stats")
    logger.info("  - Callbacks: role_channel_owner, role_advertiser, add_channel, browse_channels")
    logger.info("  - Callbacks: purchase, confirm_purchase, my_orders")
    logger.info("  - FSM: ChannelRegistration, PurchaseFlow states")
