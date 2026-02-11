"""
Telegram Bot Handlers - PHASE 2: PURCHASE FLOW
Complete implementation with browse, purchase, and order management
"""

import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import os

logger = logging.getLogger(__name__)
router = Router()

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:10000")


# ============================================================================
# FSM STATES
# ============================================================================

class ChannelRegistration(StatesGroup):
    waiting_for_forward = State()
    waiting_for_pricing = State()


class PurchaseFlow(StatesGroup):
    selecting_ad_type = State()
    confirming_purchase = State()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def api_request(method: str, endpoint: str, **kwargs):
    """Make API request to backend"""
    url = f"{API_BASE_URL}{endpoint}"
    logger.info(f"🔗 API {method} {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                logger.info(f"📥 Response: {response.status}")
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API Error {response.status}: {error_text}")
                    return {"error": error_text}
    except Exception as e:
        logger.error(f"❌ Request failed: {e}")
        return {"error": str(e)}


async def check_bot_admin_status(message: Message, channel_id: int) -> dict:
    """Check if bot is admin in the channel"""
    try:
        bot = message.bot
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        
        logger.info(f"Bot status in channel {channel_id}: {bot_member.status}")
        
        is_admin = bot_member.status in ["administrator", "creator"]
        can_post = False
        
        if bot_member.status == "creator":
            can_post = True
        elif bot_member.status == "administrator":
            can_post = getattr(bot_member, 'can_post_messages', False)
        
        return {"is_admin": is_admin, "can_post": can_post}
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return {"is_admin": False, "can_post": False}


def create_main_menu_keyboard(is_owner=False, is_advertiser=False):
    """Create main menu keyboard based on user roles"""
    keyboard = []
    
    if not is_owner and not is_advertiser:
        keyboard = [
            [InlineKeyboardButton(text="📢 I'm a Channel Owner", callback_data="role_channel_owner")],
            [InlineKeyboardButton(text="🎯 I'm an Advertiser", callback_data="role_advertiser")]
        ]
    else:
        if is_owner:
            keyboard.append([InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")])
            keyboard.append([InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")])
        
        if is_advertiser:
            keyboard.append([InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")])
            keyboard.append([InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")])
        
        if is_owner and not is_advertiser:
            keyboard.append([InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")])
        elif is_advertiser and not is_owner:
            keyboard.append([InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_channel_owner_menu():
    """Create channel owner menu"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_advertiser_menu():
    """Create advertiser menu"""
    keyboard = [
        [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - WITH DATABASE"""
    logger.info(f"/start from user {message.from_user.id}")
    await state.clear()
    
    # Register/get user in database
    result = await api_request(
        "POST", "/users/",
        params={
            "telegram_id": message.from_user.id,
            "username": message.from_user.username or "",
            "first_name": message.from_user.first_name or ""
        }
    )
    
    if "error" in result:
        logger.error(f"User registration failed: {result['error']}")
        is_owner = False
        is_advertiser = False
    else:
        is_owner = result.get("is_channel_owner", False)
        is_advertiser = result.get("is_advertiser", False)
    
    welcome_text = (
        f"👋 Welcome to Telegram Ads Marketplace!\n\n"
        f"Connect channel owners with advertisers.\n\n"
        f"Your Profile:\n"
        f"Name: {message.from_user.first_name or 'User'}\n"
        f"Username: @{message.from_user.username or 'Not set'}\n\n"
        f"How would you like to use the marketplace?"
    )
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    await message.answer(welcome_text, reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 Telegram Ads Marketplace\n\n"
        "For Channel Owners:\n"
        "• Add channels\n"
        "• Set pricing\n"
        "• Earn money\n\n"
        "For Advertisers:\n"
        "• Browse channels\n"
        "• Purchase ads\n"
        "• Track orders\n\n"
        "Commands:\n"
        "/start - Main menu\n"
        "/help - This message\n"
        "/stats - Statistics"
    )
    await message.answer(help_text)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command - WITH REAL DATABASE DATA"""
    stats = await api_request("GET", "/stats")
    
    if "error" in stats:
        logger.error(f"Stats fetch failed: {stats['error']}")
        stats_text = (
            "📊 Statistics\n\n"
            "👥 Users: 0\n"
            "📢 Channels: 0\n"
            "💼 Orders: 0\n"
            "🔥 Active: 0"
        )
    else:
        stats_text = (
            "📊 Marketplace Statistics\n\n"
            f"👥 Users: {stats.get('total_users', 0)}\n"
            f"📢 Channels: {stats.get('total_channels', 0)}\n"
            f"💼 Orders: {stats.get('total_orders', 0)}\n"
            f"🔥 Active: {stats.get('active_orders', 0)}"
        )
    
    await message.answer(stats_text)


# ============================================================================
# ROLE CALLBACKS
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    """Handle channel owner role selection - WITH DATABASE"""
    logger.info(f"role_channel_owner from {callback.from_user.id}")
    
    # Update user role in database (JSON body)
    result = await api_request(
        "PATCH", f"/users/{callback.from_user.id}",
        json={"is_channel_owner": True}
    )
    
    if "error" in result:
        await callback.answer("Failed to update role. Try again.", show_alert=True)
    else:
        await callback.answer("✅ Role updated! You are now a Channel Owner.", show_alert=False)
    
    text = "Channel Owner Menu\n\nList your channels and earn money!"
    await callback.message.edit_text(text, reply_markup=create_channel_owner_menu())


@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    """Handle advertiser role selection - WITH DATABASE"""
    logger.info(f"role_advertiser from {callback.from_user.id}")
    
    # Update user role in database (JSON body)
    result = await api_request(
        "PATCH", f"/users/{callback.from_user.id}",
        json={"is_advertiser": True}
    )
    
    if "error" in result:
        await callback.answer("Failed to update role. Try again.", show_alert=True)
    else:
        await callback.answer("✅ Role updated! You are now an Advertiser.", show_alert=False)
    
    text = "Advertiser Menu\n\nFind channels for your ads!"
    await callback.message.edit_text(text, reply_markup=create_advertiser_menu())


# ============================================================================
# CHANNEL MANAGEMENT
# ============================================================================

@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    """Start channel registration"""
    logger.info(f"add_channel from {callback.from_user.id}")
    
    try:
        await state.clear()
        
        text = (
            "Add Your Channel\n\n"
            "Steps:\n"
            "1. Add the bot as Administrator to your channel\n"
            "2. Enable Post Messages permission\n"
            "3. Forward any message from your channel here\n\n"
            "Bot will verify admin access before registration."
        )
        
        await callback.message.edit_text(text)
        await state.set_state(ChannelRegistration.waiting_for_forward)
        await callback.answer("Ready! Forward a message from your channel.")
        
        logger.info("add_channel completed successfully")
        
    except Exception as e:
        logger.error(f"Error in add_channel: {e}", exc_info=True)
        await callback.answer("Error. Try /start", show_alert=True)


@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded channel message - WITH DATABASE"""
    logger.info(f"Channel forward from {message.from_user.id}")
    
    try:
        if not message.forward_from_chat or message.forward_from_chat.type != "channel":
            await message.answer("❌ Please forward a message FROM a Telegram channel.")
            return
        
        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title or "Unknown Channel"
        channel_username = message.forward_from_chat.username
        
        logger.info(f"Channel: {channel_title} ({channel_id})")
        
        # Check admin status
        admin_check = await check_bot_admin_status(message, channel_id)
        
        if not admin_check["is_admin"]:
            text = (
                f"❌ Bot Not Admin\n\n"
                f"I'm not admin in {channel_title}!\n\n"
                f"Fix:\n"
                f"1. Open {channel_title}\n"
                f"2. Settings → Administrators\n"
                f"3. Add the bot\n"
                f"4. Enable Post Messages\n"
                f"5. Try again"
            )
            await message.answer(text)
            await state.clear()
            logger.info(f"Rejected: Not admin in {channel_id}")
            return
        
        if not admin_check["can_post"]:
            text = (
                f"⚠️ No Post Permission\n\n"
                f"I'm admin but can't post in {channel_title}!\n\n"
                f"Fix:\n"
                f"1. {channel_title} → Administrators\n"
                f"2. Tap the bot\n"
                f"3. Enable Post Messages\n"
                f"4. Try again"
            )
            await message.answer(text)
            await state.clear()
            logger.info(f"Rejected: Can't post in {channel_id}")
            return
        
        # SUCCESS - Save to state for pricing
        await state.update_data(
            channel_id=channel_id,
            channel_title=channel_title,
            channel_username=channel_username
        )
        
        text = (
            f"✅ Channel Verified!\n\n"
            f"📢 {channel_title}\n"
            f"🔗 {channel_username or 'Private'}\n\n"
            f"✅ Admin confirmed\n"
            f"✅ Can post messages\n\n"
            f"💰 Set Pricing:\n\n"
            f"Send in this format:\n"
            f"post: 100\n"
            f"story: 50\n"
            f"repost: 25"
        )
        
        await message.answer(text)
        await state.set_state(ChannelRegistration.waiting_for_pricing)
        
        logger.info(f"Admin verified for {channel_id}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await message.answer("❌ Error. Try again.")
        await state.clear()


@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    """Process pricing - SAVE TO DATABASE"""
    try:
        data = await state.get_data()
        if not data:
            await message.answer("❌ No channel data. Start with /start")
            await state.clear()
            return
        
        # Parse pricing
        pricing = {}
        for line in message.text.strip().lower().split('\n'):
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    try:
                        value = float(parts[1].strip())
                        if key in ['post', 'story', 'repost']:
                            pricing[key] = value
                    except:
                        pass
        
        if not pricing:
            text = (
                "❌ Invalid format.\n\n"
                "Send like:\n"
                "post: 100\n"
                "story: 50\n"
                "repost: 25"
            )
            await message.answer(text)
            return
        
        # SAVE TO DATABASE via API
        result = await api_request(
            "POST", "/channels/",
            json={
                "owner_telegram_id": message.from_user.id,
                "telegram_channel_id": data["channel_id"],
                "channel_title": data["channel_title"],
                "channel_username": data["channel_username"],
                "pricing": pricing
            }
        )
        
        if "error" in result:
            if "already exists" in str(result.get("error", "")).lower():
                await message.answer(f"{data['channel_title']} already listed in database!")
            else:
                await message.answer(f"Database error: {result.get('error')}\n\nPlease try again.")
        else:
            pricing_str = "\n".join([f"• {k}: {v} USD" for k, v in pricing.items()])
            
            text = (
                f"Channel Saved to Database!\n\n"
                f"Channel: {data['channel_title']}\n"
                f"Pricing:\n{pricing_str}\n\n"
                f"Stored permanently!\n"
                f"Database ID: {result.get('id')}"
            )
            
            await message.answer(text)
            
            # Show success notification
            await message.answer("✅ SUCCESS! Your channel is now live in the marketplace!")
        
        await state.clear()
        
        logger.info(f"Registered in DB: {data['channel_title']} with pricing {pricing}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await message.answer("❌ Error saving to database. Try again.")
        await state.clear()


@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """Show user's channels - FROM DATABASE"""
    logger.info(f"my_channels from {callback.from_user.id}")
    
    # Fetch user's channels from database
    channels = await api_request("GET", f"/channels/owner/{callback.from_user.id}")
    
    if "error" in channels or not channels:
        text = "📊 My Channels\n\nYou haven't added any channels yet.\n\nUse 'Add My Channel' to get started!"
    else:
        text = f"📊 My Channels ({len(channels)} total)\n\n"
        for channel in channels[:10]:
            pricing = channel.get("pricing", {})
            pricing_text = ", ".join([f"{k}: {v} USD" for k, v in pricing.items()])
            text += f"Channel: {channel['channel_title']}\n"
            text += f"   Pricing: {pricing_text}\n"
            text += f"   Status: {channel['status']}\n\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


# ============================================================================
# BROWSE CHANNELS - PHASE 2 ENHANCED
# ============================================================================

@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery, state: FSMContext):
    """Browse channels - ENHANCED WITH PURCHASE BUTTONS"""
    logger.info(f"browse_channels from {callback.from_user.id}")
    
    await state.clear()
    
    # Fetch channels from database
    channels = await api_request("GET", "/channels/")
    
    if "error" in channels or not isinstance(channels, list) or len(channels) == 0:
        text = "🔍 Browse Channels\n\nNo channels available yet.\n\nCheck back soon!"
        await callback.message.edit_text(text)
        await callback.answer()
        return
    
    # Show first channel with purchase option
    await show_channel_detail(callback.message, channels[0], 0, len(channels), callback.from_user.id)
    await callback.answer()


async def show_channel_detail(message, channel: dict, index: int, total: int, user_id: int):
    """Show detailed channel view with purchase button"""
    pricing = channel.get("pricing", {})
    
    # Build pricing display
    pricing_lines = []
    for ad_type, price in pricing.items():
        pricing_lines.append(f"  • {ad_type.capitalize()}: {price} USD")
    
    pricing_text = "\n".join(pricing_lines) if pricing_lines else "  No pricing set"
    
    text = (
        f"Channel {index + 1} of {total}\n\n"
        f"Channel: {channel['channel_title']}\n"
        f"Username: @{channel.get('channel_username', 'Private')}\n"
        f"Subscribers: {channel.get('subscribers', 0):,}\n"
        f"Avg Views: {channel.get('avg_views', 0):,}\n\n"
        f"Pricing:\n{pricing_text}\n\n"
        f"Status: {channel['status']}"
    )
    
    # Build navigation keyboard
    keyboard = []
    
    # Purchase button
    keyboard.append([InlineKeyboardButton(
        text="🛒 Purchase Ad",
        callback_data=f"purchase_channel_{channel['id']}"
    )])
    
    # Navigation buttons
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"channel_nav_{index-1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"channel_nav_{index+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    
    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data.startswith("channel_nav_"))
async def callback_channel_navigation(callback: CallbackQuery):
    """Handle channel navigation"""
    index = int(callback.data.split("_")[-1])
    
    # Fetch channels
    channels = await api_request("GET", "/channels/")
    
    if "error" not in channels and isinstance(channels, list) and len(channels) > index:
        await show_channel_detail(callback.message, channels[index], index, len(channels), callback.from_user.id)
    
    await callback.answer()


# ============================================================================
# PURCHASE FLOW - PHASE 2
# ============================================================================

@router.callback_query(F.data.startswith("purchase_channel_"))
async def callback_purchase_channel(callback: CallbackQuery, state: FSMContext):
    """Start purchase flow for a channel"""
    channel_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Purchase initiated for channel {channel_id} by user {callback.from_user.id}")
    
    # Fetch channel details
    channel = await api_request("GET", f"/channels/{channel_id}")
    
    if "error" in channel:
        await callback.answer("❌ Channel not found!", show_alert=True)
        return
    
    # Save channel to state
    await state.update_data(
        channel_id=channel_id,
        channel_title=channel['channel_title'],
        pricing=channel['pricing']
    )
    
    # Show ad type selection
    pricing = channel['pricing']
    
    text = (
        f"🛒 Purchase Ad Slot\n\n"
        f"📢 {channel['channel_title']}\n\n"
        f"Select ad type:"
    )
    
    keyboard = []
    for ad_type, price in pricing.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{ad_type.capitalize()} - {price} USD",
            callback_data=f"select_adtype_{ad_type}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="browse_channels")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(PurchaseFlow.selecting_ad_type)
    await callback.answer()


@router.callback_query(F.data.startswith("select_adtype_"), StateFilter(PurchaseFlow.selecting_ad_type))
async def callback_select_ad_type(callback: CallbackQuery, state: FSMContext):
    """Handle ad type selection"""
    ad_type = callback.data.split("_")[-1]
    
    # Get state data
    data = await state.get_data()
    pricing = data.get('pricing', {})
    price = pricing.get(ad_type, 0)
    
    # Update state
    await state.update_data(ad_type=ad_type, price=price)
    
    text = (
        f"Confirm Purchase\n\n"
        f"Channel: {data['channel_title']}\n"
        f"Ad Type: {ad_type.capitalize()}\n"
        f"Price: {price} USD\n\n"
        f"Confirm this order?"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="Confirm Order", callback_data="confirm_purchase")],
        [InlineKeyboardButton(text="Cancel", callback_data="browse_channels")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(PurchaseFlow.confirming_purchase)
    await callback.answer()


@router.callback_query(F.data == "confirm_purchase", StateFilter(PurchaseFlow.confirming_purchase))
async def callback_confirm_purchase(callback: CallbackQuery, state: FSMContext):
    """Confirm and create order"""
    data = await state.get_data()
    
    logger.info(f"Creating order: channel={data['channel_id']}, type={data['ad_type']}, price={data['price']}")
    
    # Show processing notification
    await callback.answer("Creating your order...", show_alert=False)
    
    # Create order in database
    result = await api_request(
        "POST", "/orders/",
        json={
            "buyer_telegram_id": callback.from_user.id,
            "channel_id": data['channel_id'],
            "ad_type": data['ad_type'],
            "price": data['price']
        }
    )
    
    if "error" in result:
        text = f"ORDER CREATION FAILED!\n\n{result.get('error')}\n\nPlease try again."
        keyboard = [[InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]]
        await callback.answer("Order creation failed!", show_alert=True)
    else:
        order_id = result.get('id')
        
        text = (
            "ORDER CREATED SUCCESSFULLY!\n\n"
            f"Order ID: {order_id}\n"
            f"Channel: {data['channel_title']}\n"
            f"Ad Type: {data['ad_type'].capitalize()}\n"
            f"Price: {data['price']} USD\n\n"
            f"Status: Pending Payment\n\n"
            f"Next: Complete payment to activate your order."
        )
        
        keyboard = [
            [InlineKeyboardButton(text="Simulate Payment", callback_data=f"pay_order_{order_id}")],
            [InlineKeyboardButton(text="My Orders", callback_data="my_orders")],
            [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
        ]
        
        logger.info(f"Order created: {order_id}")
        await callback.answer("✅ Order created! Proceed to payment.", show_alert=True)
    
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to update message: {e}")
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await state.clear()


# ============================================================================
# PAYMENT SIMULATION - PHASE 2
# ============================================================================

@router.callback_query(F.data.startswith("pay_order_"))
async def callback_pay_order(callback: CallbackQuery):
    """Simulate payment for an order"""
    from datetime import datetime
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Payment simulation for order {order_id}")
    
    # Show processing notification
    await callback.answer("Processing payment...", show_alert=False)
    
    # Update order status to paid
    result = await api_request(
        "PATCH", f"/orders/{order_id}",
        json={
            "status": "paid",
            "payment_method": "simulated",
            "payment_transaction_id": f"SIM{order_id}_{int(datetime.utcnow().timestamp())}",
            "paid_at": datetime.utcnow().isoformat()
        }
    )
    
    if "error" in result:
        text = (
            "PAYMENT FAILED!\n\n"
            f"Order ID: {order_id}\n"
            f"Error: {result.get('error')}\n\n"
            "Please try again or contact support."
        )
        logger.error(f"Payment failed for order {order_id}: {result.get('error')}")
        
        # Show error notification
        await callback.answer("Payment failed! Please try again.", show_alert=True)
    else:
        tx_id = result.get('payment_transaction_id', 'N/A')
        text = (
            "PAYMENT SUCCESSFUL!\n\n"
            f"Order ID: {order_id}\n"
            f"Status: Paid\n"
            f"Transaction: {tx_id}\n\n"
            "Your order is now being processed.\n"
            "The channel owner will be notified."
        )
        
        logger.info(f"Order {order_id} paid successfully")
        
        # Show success notification with alert
        await callback.answer("✅ Payment successful! Your order is confirmed.", show_alert=True)
    
    keyboard = [
        [InlineKeyboardButton(text="My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
    ]
    
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to update message: {e}")
        # If edit fails, send new message
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


# ============================================================================
# ORDER MANAGEMENT - PHASE 2 ENHANCED
# ============================================================================

@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """Show user's orders - ENHANCED FROM DATABASE"""
    logger.info(f"my_orders from {callback.from_user.id}")
    
    # Fetch orders from database
    orders = await api_request("GET", f"/orders/user/{callback.from_user.id}")
    
    if "error" in orders or not orders:
        text = (
            "🛒 My Orders\n\n"
            "You haven't placed any orders yet.\n\n"
            "Browse channels to get started!"
        )
        keyboard = [
            [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        ]
    else:
        text = f"🛒 My Orders ({len(orders)} total)\n\n"
        
        for order in orders[:10]:
            status_emoji = {
                "pending_payment": "⏳",
                "paid": "✅",
                "processing": "🔄",
                "completed": "✅",
                "cancelled": "❌",
                "refunded": "💰"
            }.get(order["status"], "❓")
            
            text += f"{status_emoji} Order {order['id']}\n"
            text += f"   Type: {order['ad_type'].capitalize()}\n"
            text += f"   Price: {order['price']} USD\n"
            text += f"   Status: {order['status'].replace('_', ' ').title()}\n"
            
            if order.get('payment_transaction_id'):
                text += f"   TX: {order['payment_transaction_id']}\n"
            
            text += "\n"
        
        if len(orders) > 10:
            text += f"...and {len(orders) - 10} more orders"
        
        keyboard = [
            [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


# ============================================================================
# MAIN MENU
# ============================================================================

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu - WITH DATABASE"""
    logger.info(f"main_menu from {callback.from_user.id}")
    await state.clear()
    
    # Get user info from database
    result = await api_request("GET", f"/users/{callback.from_user.id}")
    
    if "error" in result:
        is_owner = False
        is_advertiser = False
    else:
        is_owner = result.get("is_channel_owner", False)
        is_advertiser = result.get("is_advertiser", False)
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    
    text = "🏠 Main Menu\n\nWhat would you like to do?"
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def setup_handlers(dp):
    """Register handlers"""
    dp.include_router(router)
    logger.info("✅ Router registered with dispatcher")
    logger.info("📝 Registered handlers with PHASE 2: PURCHASE FLOW")
