"""
Telegram Bot Handlers - PHASE 5: PREMIUM UI DESIGN
World-class user interface with professional styling
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
import aiohttp
import os
from datetime import datetime
from ui_design import *

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


class CreativeSubmission(StatesGroup):
    waiting_for_content = State()
    waiting_for_media = State()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def api_request(method: str, endpoint: str, **kwargs):
    """Make API request to backend"""
    url = f"{API_BASE_URL}{endpoint}"
    logger.info(f"API {method} {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                logger.info(f"Response: {response.status}")
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    return {"error": error_text}
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {"error": str(e)}


async def send_notification(bot, telegram_id: int, message: str):
    """Send notification to user"""
    try:
        await bot.send_message(chat_id=telegram_id, text=message)
        logger.info(f"Notification sent to {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")


async def notify_order_status_change(bot, order_id: int, old_status: str, new_status: str):
    """Notify relevant parties when order status changes"""
    # Get order details
    order = await api_request("GET", f"/orders/{order_id}")
    if "error" in order:
        return
    
    buyer_telegram_id = order.get('buyer_telegram_id')
    
    # Notification messages based on status
    if new_status == "paid":
        message = f"Order {order_id} payment confirmed - Submit your creative now"
        await send_notification(bot, buyer_telegram_id, message)
    
    elif new_status == "creative_submitted":
        message = f"Order {order_id} creative submitted - Waiting for channel owner approval"
        await send_notification(bot, buyer_telegram_id, message)
        
        # Notify channel owner
        channel = await api_request("GET", f"/channels/{order['channel_id']}")
        if "error" not in channel:
            owner = await api_request("GET", f"/users/telegram/{channel['owner_telegram_id']}")
            if "error" not in owner:
                owner_message = f"New order {order_id} waiting for review - Check Pending Orders"
                await send_notification(bot, channel['owner_telegram_id'], owner_message)
    
    elif new_status == "posted":
        message = f"Order {order_id} approved and posted to channel - Check My Orders for details"
        await send_notification(bot, buyer_telegram_id, message)


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
            [InlineKeyboardButton(text="I am a Channel Owner", callback_data="role_channel_owner")],
            [InlineKeyboardButton(text="I am an Advertiser", callback_data="role_advertiser")]
        ]
    else:
        if is_owner:
            keyboard.append([InlineKeyboardButton(text="Add My Channel", callback_data="add_channel")])
            keyboard.append([InlineKeyboardButton(text="My Channels", callback_data="my_channels")])
            keyboard.append([InlineKeyboardButton(text="Pending Orders", callback_data="pending_orders")])
        
        if is_advertiser:
            keyboard.append([InlineKeyboardButton(text="Browse Channels", callback_data="browse_channels")])
            keyboard.append([InlineKeyboardButton(text="My Orders", callback_data="my_orders")])
        
        if is_owner and not is_advertiser:
            keyboard.append([InlineKeyboardButton(text="I also want to Advertise", callback_data="role_advertiser")])
        elif is_advertiser and not is_owner:
            keyboard.append([InlineKeyboardButton(text="I also have a Channel", callback_data="role_channel_owner")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_channel_owner_menu():
    """Create channel owner menu"""
    keyboard = [
        [InlineKeyboardButton(text="Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="My Earnings", callback_data="my_earnings")],
        [InlineKeyboardButton(text="Pending Orders", callback_data="pending_orders")],
        [InlineKeyboardButton(text="I also want to Advertise", callback_data="role_advertiser")],
        [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_advertiser_menu():
    """Create advertiser menu"""
    keyboard = [
        [InlineKeyboardButton(text="Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="I also have a Channel", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
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
    
    # Premium welcome message
    welcome_text = f"{EMOJI['party']} Welcome to AdMarket!\n\n"
    welcome_text += f"Hello {message.from_user.first_name or 'User'}! {EMOJI['rocket']}\n\n"
    welcome_text += f"{create_separator('stars')}\n\n"
    welcome_text += f"{EMOJI['broadcast']} Connect channels with advertisers\n"
    welcome_text += f"{EMOJI['money']} Earn money or grow your brand\n"
    welcome_text += f"{EMOJI['chart_up']} Professional ad marketplace\n\n"
    welcome_text += f"{create_separator('light')}\n\n"
    welcome_text += f"{EMOJI['user']} Your Profile:\n"
    welcome_text += f"  {EMOJI['badge']} {message.from_user.first_name or 'User'}\n"
    welcome_text += f"  {EMOJI['link']} @{message.from_user.username or 'Not set'}\n\n"
    welcome_text += f"{EMOJI['target']} Choose your role below:"
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    await message.answer(welcome_text, reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = f"{EMOJI['info']} AdMarket Help Center\n\n"
    help_text += f"{create_separator('medium')}\n\n"
    help_text += f"{EMOJI['owner']} For Channel Owners:\n"
    help_text += f"  {EMOJI['add']} Add your channels\n"
    help_text += f"  {EMOJI['money']} Set custom pricing\n"
    help_text += f"  {EMOJI['approve']} Approve ad creatives\n"
    help_text += f"  {EMOJI['profit']} Track earnings\n\n"
    help_text += f"{EMOJI['advertiser']} For Advertisers:\n"
    help_text += f"  {EMOJI['browse']} Browse channels\n"
    help_text += f"  {EMOJI['shop']} Purchase ad slots\n"
    help_text += f"  {EMOJI['send']} Submit creatives\n"
    help_text += f"  {EMOJI['order']} Track orders\n\n"
    help_text += f"{create_separator('light')}\n\n"
    help_text += f"{EMOJI['menu']} Commands:\n"
    help_text += f"  /start - Main menu\n"
    help_text += f"  /help - This message\n"
    help_text += f"  /stats - View statistics"
    await message.answer(help_text)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command"""
    stats = await api_request("GET", "/stats")
    
    if "error" in stats:
        logger.error(f"Stats fetch failed: {stats['error']}")
        stats_text = f"{EMOJI['chart_up']} Marketplace Statistics\n\n"
        stats_text += f"{create_separator('light')}\n\n"
        stats_text += f"{EMOJI['users']} Users: 0\n"
        stats_text += f"{EMOJI['channel']} Channels: 0\n"
        stats_text += f"{EMOJI['order']} Orders: 0\n"
        stats_text += f"{EMOJI['fire']} Active: 0"
    else:
        stats_text = f"{EMOJI['dashboard']} Marketplace Statistics\n\n"
        stats_text += f"{create_separator('stars')}\n\n"
        stats_text += f"{EMOJI['users']} Total Users: {stats.get('total_users', 0)}\n"
        stats_text += f"{EMOJI['channel']} Total Channels: {stats.get('total_channels', 0)}\n"
        stats_text += f"{EMOJI['order']} Total Orders: {stats.get('total_orders', 0)}\n"
        stats_text += f"{EMOJI['fire']} Active Now: {stats.get('active_orders', 0)}\n\n"
        stats_text += f"{create_separator('light')}\n\n"
        stats_text += f"{EMOJI['rocket']} Platform growing daily!"
    
    await message.answer(stats_text)


# ============================================================================
# ROLE CALLBACKS
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    """Handle channel owner role selection"""
    logger.info(f"role_channel_owner from {callback.from_user.id}")
    
    # Update user role in database
    result = await api_request(
        "PATCH", f"/users/{callback.from_user.id}",
        json={"is_channel_owner": True}
    )
    
    if "error" in result:
        await callback.answer("Failed to update role - Try again", show_alert=True)
    else:
        await callback.answer(f"{EMOJI['success']} Role updated successfully!", show_alert=False)
    
    text = f"{EMOJI['owner']} Channel Owner Dashboard\n\n"
    text += f"{create_separator('stars')}\n\n"
    text += f"{EMOJI['money']} List your channels and earn money\n"
    text += f"{EMOJI['chart_up']} Set your own pricing\n"
    text += f"{EMOJI['approve']} Approve quality ads\n"
    text += f"{EMOJI['profit']} Track your earnings\n\n"
    text += f"{create_separator('light')}\n\n"
    text += f"{EMOJI['target']} Choose an action below:"
    
    await callback.message.edit_text(text, reply_markup=create_channel_owner_menu())


@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    """Handle advertiser role selection"""
    logger.info(f"role_advertiser from {callback.from_user.id}")
    
    # Update user role in database
    result = await api_request(
        "PATCH", f"/users/{callback.from_user.id}",
        json={"is_advertiser": True}
    )
    
    if "error" in result:
        await callback.answer("Failed to update role - Try again", show_alert=True)
    else:
        await callback.answer(f"{EMOJI['success']} Role updated successfully!", show_alert=False)
    
    text = f"{EMOJI['advertiser']} Advertiser Dashboard\n\n"
    text += f"{create_separator('stars')}\n\n"
    text += f"{EMOJI['browse']} Find perfect channels for your ads\n"
    text += f"{EMOJI['shop']} Purchase ad slots easily\n"
    text += f"{EMOJI['send']} Submit creative content\n"
    text += f"{EMOJI['chart_up']} Track campaign performance\n\n"
    text += f"{create_separator('light')}\n\n"
    text += f"{EMOJI['target']} Choose an action below:"
    
    await callback.message.edit_text(text, reply_markup=create_advertiser_menu())


# ============================================================================
# CHANNEL MANAGEMENT (FROM PHASE 1 & 2)
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
            "Bot will verify admin access before registration"
        )
        
        await callback.message.edit_text(text)
        await state.set_state(ChannelRegistration.waiting_for_forward)
        await callback.answer("Ready - Forward a message from your channel")
        
        logger.info("add_channel completed successfully")
        
    except Exception as e:
        logger.error(f"Error in add_channel: {e}", exc_info=True)
        await callback.answer("Error - Try /start", show_alert=True)


@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded channel message"""
    logger.info(f"Channel forward from {message.from_user.id}")
    
    try:
        if not message.forward_from_chat or message.forward_from_chat.type != "channel":
            await message.answer("Please forward a message FROM a Telegram channel")
            return
        
        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title or "Unknown Channel"
        channel_username = message.forward_from_chat.username
        
        logger.info(f"Channel: {channel_title} ({channel_id})")
        
        # Check admin status
        admin_check = await check_bot_admin_status(message, channel_id)
        
        if not admin_check["is_admin"]:
            text = (
                f"Bot Not Admin\n\n"
                f"I am not admin in {channel_title}\n\n"
                f"Fix:\n"
                f"1. Open {channel_title}\n"
                f"2. Settings > Administrators\n"
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
                f"No Post Permission\n\n"
                f"I am admin but cannot post in {channel_title}\n\n"
                f"Fix:\n"
                f"1. {channel_title} > Administrators\n"
                f"2. Tap the bot\n"
                f"3. Enable Post Messages\n"
                f"4. Try again"
            )
            await message.answer(text)
            await state.clear()
            logger.info(f"Rejected: Cannot post in {channel_id}")
            return
        
        # SUCCESS - Save to state for pricing
        await state.update_data(
            channel_id=channel_id,
            channel_title=channel_title,
            channel_username=channel_username
        )
        
        text = (
            f"Channel Verified\n\n"
            f"Channel: {channel_title}\n"
            f"Link: {channel_username or 'Private'}\n\n"
            f"Admin confirmed\n"
            f"Can post messages\n\n"
            f"Set Pricing:\n\n"
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
        await message.answer("Error - Try again")
        await state.clear()


@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    """Process pricing - SAVE TO DATABASE"""
    try:
        data = await state.get_data()
        if not data:
            await message.answer("No channel data - Start with /start")
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
                "Invalid format\n\n"
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
                await message.answer(f"{data['channel_title']} already listed in database")
            else:
                await message.answer(f"Database error: {result.get('error')}\n\nPlease try again")
        else:
            pricing_str = "\n".join([f"- {k}: {v} USD" for k, v in pricing.items()])
            
            text = (
                f"Channel Saved to Database\n\n"
                f"Channel: {data['channel_title']}\n"
                f"Pricing:\n{pricing_str}\n\n"
                f"Stored permanently\n"
                f"Database ID: {result.get('id')}"
            )
            
            await message.answer(text)
            await message.answer("SUCCESS - Your channel is now live in the marketplace")
        
        await state.clear()
        
        logger.info(f"Registered in DB: {data['channel_title']} with pricing {pricing}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await message.answer("Error saving to database - Try again")
        await state.clear()


@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """Show user's channels"""
    logger.info(f"my_channels from {callback.from_user.id}")
    
    # Fetch user's channels from database
    channels = await api_request("GET", f"/channels/owner/{callback.from_user.id}")
    
    if "error" in channels or not channels:
        text = "My Channels\n\nYou have not added any channels yet\n\nUse Add My Channel to get started"
    else:
        text = f"My Channels ({len(channels)} total)\n\n"
        for channel in channels[:10]:
            pricing = channel.get("pricing", {})
            pricing_text = ", ".join([f"{k}: {v} USD" for k, v in pricing.items()])
            text += f"Channel: {channel['channel_title']}\n"
            text += f"   Pricing: {pricing_text}\n"
            text += f"   Status: {channel['status']}\n\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "my_earnings")
async def callback_my_earnings(callback: CallbackQuery):
    """Show channel owner earnings dashboard"""
    logger.info(f"my_earnings from {callback.from_user.id}")
    
    # Fetch user's channels
    channels = await api_request("GET", f"/channels/owner/{callback.from_user.id}")
    
    if "error" in channels or not channels:
        text = "Earnings Dashboard\n\nYou have no channels yet\n\nAdd a channel to start earning"
        await callback.message.edit_text(text)
        await callback.answer()
        return
    
    # Calculate total earnings
    total_earnings = 0.0
    total_orders = 0
    completed_orders = 0
    pending_orders = 0
    
    channel_earnings = []
    
    for channel in channels:
        # Get orders for this channel
        orders = await api_request("GET", f"/orders/channel/{channel['id']}")
        
        if "error" not in orders and orders:
            channel_total = 0.0
            channel_completed = 0
            channel_pending = 0
            
            for order in orders:
                total_orders += 1
                if order['status'] in ['posted', 'completed']:
                    channel_total += order['price']
                    channel_completed += 1
                    completed_orders += 1
                elif order['status'] in ['paid', 'creative_submitted']:
                    channel_pending += 1
                    pending_orders += 1
            
            total_earnings += channel_total
            
            if channel_completed > 0 or channel_pending > 0:
                channel_earnings.append({
                    'name': channel['channel_title'],
                    'earned': channel_total,
                    'completed': channel_completed,
                    'pending': channel_pending
                })
    
    # Build earnings report
    text = "Earnings Dashboard\n\n"
    text += f"Total Earnings {total_earnings} USD\n"
    text += f"Total Orders {total_orders}\n"
    text += f"Completed {completed_orders}\n"
    text += f"Pending {pending_orders}\n\n"
    
    if channel_earnings:
        text += "Per Channel\n\n"
        for ch in channel_earnings:
            text += f"{ch['name']}\n"
            text += f"  Earned {ch['earned']} USD\n"
            text += f"  Completed {ch['completed']} orders\n"
            text += f"  Pending {ch['pending']} orders\n\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


# ============================================================================
# BROWSE CHANNELS (FROM PHASE 2)
# ============================================================================

@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery, state: FSMContext):
    """Browse channels"""
    logger.info(f"browse_channels from {callback.from_user.id}")
    
    await state.clear()
    
    # Fetch channels from database
    channels = await api_request("GET", "/channels/")
    
    if "error" in channels or not isinstance(channels, list) or len(channels) == 0:
        text = "Browse Channels\n\nNo channels available yet\n\nCheck back soon"
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
        pricing_lines.append(f"  - {ad_type.capitalize()}: {price} USD")
    
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
        text="Purchase Ad",
        callback_data=f"purchase_channel_{channel['id']}"
    )])
    
    # Navigation buttons
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="Previous", callback_data=f"channel_nav_{index-1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="Next", callback_data=f"channel_nav_{index+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton(text="Main Menu", callback_data="main_menu")])
    
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
# PURCHASE FLOW (FROM PHASE 2)
# ============================================================================

@router.callback_query(F.data.startswith("purchase_channel_"))
async def callback_purchase_channel(callback: CallbackQuery, state: FSMContext):
    """Start purchase flow for a channel"""
    channel_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Purchase initiated for channel {channel_id} by user {callback.from_user.id}")
    
    # Fetch channel details
    channel = await api_request("GET", f"/channels/{channel_id}")
    
    if "error" in channel:
        await callback.answer("Channel not found", show_alert=True)
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
        f"Purchase Ad Slot\n\n"
        f"Channel: {channel['channel_title']}\n\n"
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
        f"Channel {data['channel_title']}\n"
        f"Ad Type {ad_type.capitalize()}\n"
        f"Price {price} USD\n\n"
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
        error_msg = str(result.get('error', 'Unknown error'))
        text = f"ORDER CREATION FAILED\n\n{error_msg}\n\nPlease try again"
        keyboard = [[InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]]
        
        await callback.message.answer("FAILED - Could not create order - Please try again")
    else:
        order_id = result.get('id')
        
        text = (
            "ORDER CREATED SUCCESSFULLY\n\n"
            f"Order ID {order_id}\n"
            f"Channel {data['channel_title']}\n"
            f"Ad Type {data['ad_type'].capitalize()}\n"
            f"Price {data['price']} USD\n\n"
            f"Status Pending Payment\n\n"
            f"Next Complete payment to activate your order"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="Simulate Payment", callback_data=f"pay_order_{order_id}")],
            [InlineKeyboardButton(text="My Orders", callback_data="my_orders")],
            [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
        ]
        
        logger.info(f"Order created: {order_id}")
        await callback.message.answer("SUCCESS - Order created - Proceed to payment")
    
    try:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        safe_text = f"Order {order_id} created successfully - Click Simulate Payment button"
        await callback.message.answer(safe_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        await callback.message.answer(text)
    
    await state.clear()
    await callback.answer()


# ============================================================================
# PAYMENT SIMULATION (FROM PHASE 2)
# ============================================================================

@router.callback_query(F.data.startswith("pay_order_"))
async def callback_pay_order(callback: CallbackQuery):
    """Simulate payment for an order"""
    from datetime import datetime
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Payment simulation for order {order_id}")
    
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
        # Payment failed
        error_msg = str(result.get('error', 'Unknown error'))
        text = (
            "PAYMENT FAILED\n\n"
            f"Order ID {order_id}\n"
            f"Error {error_msg}\n\n"
            "Please try again or contact support"
        )
        logger.error(f"Payment failed for order {order_id}: {error_msg}")
        
        await callback.message.answer("PAYMENT FAILED - Please try again")
        
    else:
        # Payment successful
        tx_id = result.get('payment_transaction_id', 'N/A')
        text = (
            "PAYMENT SUCCESSFUL\n\n"
            f"Order ID {order_id}\n"
            f"Status Paid\n\n"
            "Your order is now being processed\n"
            "Next step Submit your ad creative\n\n"
            "Go to My Orders to submit creative"
        )
        
        logger.info(f"Order {order_id} paid successfully")
        
        await callback.message.answer("SUCCESS - Payment completed - Your order is confirmed - Submit creative next")
    
    keyboard = [
        [InlineKeyboardButton(text="My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
    ]
    
    # Send details as new message
    try:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        # Ultra safe fallback - absolute bare minimum
        await callback.message.answer(f"Payment complete - Order {order_id} - Check My Orders")
    
    await callback.answer()


# ============================================================================
# MY ORDERS - PHASE 3 ENHANCED WITH CREATIVE SUBMISSION
# ============================================================================

@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """Show user's orders with action buttons"""
    logger.info(f"my_orders from {callback.from_user.id}")
    
    # Fetch orders from database
    orders = await api_request("GET", f"/orders/user/{callback.from_user.id}")
    
    if "error" in orders or not orders:
        text = (
            "My Orders\n\n"
            "You have not placed any orders yet\n\n"
            "Browse channels to get started"
        )
        keyboard = [
            [InlineKeyboardButton(text="Browse Channels", callback_data="browse_channels")],
            [InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]
        ]
    else:
        text = f"My Orders ({len(orders)} total)\n\n"
        
        keyboard = []
        
        for order in orders[:5]:  # Show only 5 most recent
            status_emoji = {
                "pending_payment": "Pending Payment",
                "paid": "Paid - Submit Creative",
                "creative_submitted": "Creative Submitted",
                "creative_approved": "Approved - Posting Soon",
                "posted": "Posted",
                "completed": "Completed",
                "cancelled": "Cancelled",
                "refunded": "Refunded"
            }.get(order["status"], "Unknown")
            
            text += f"Order {order['id']} - {order['ad_type'].capitalize()}\n"
            text += f"Status {status_emoji}\n"
            text += f"Price {order['price']} USD\n\n"
            
            # Add action button based on status
            if order["status"] == "pending_payment":
                keyboard.append([InlineKeyboardButton(
                    text=f"Cancel Order {order['id']}",
                    callback_data=f"cancel_order_{order['id']}"
                )])
            elif order["status"] == "paid":
                keyboard.append([InlineKeyboardButton(
                    text=f"Submit Creative for Order {order['id']}",
                    callback_data=f"submit_creative_{order['id']}"
                )])
            elif order["status"] in ["creative_submitted", "creative_approved", "posted"]:
                keyboard.append([InlineKeyboardButton(
                    text=f"View Order {order['id']} Details",
                    callback_data=f"view_order_{order['id']}"
                )])
        
        if len(orders) > 5:
            text += f"...and {len(orders) - 5} more orders"
        
        keyboard.append([InlineKeyboardButton(text="Browse Channels", callback_data="browse_channels")])
        keyboard.append([InlineKeyboardButton(text="Main Menu", callback_data="main_menu")])
    
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await callback.answer()


# ============================================================================
# CREATIVE SUBMISSION - PHASE 3 NEW
# ============================================================================

@router.callback_query(F.data.startswith("submit_creative_"))
async def callback_submit_creative(callback: CallbackQuery, state: FSMContext):
    """Start creative submission process"""
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Creative submission started for order {order_id}")
    
    # Save order ID to state
    await state.update_data(order_id=order_id)
    
    text = (
        f"Submit Creative for Order {order_id}\n\n"
        f"Step 1: Send your ad text\n\n"
        f"Type the text you want in your ad\n"
        f"You can include emojis and formatting\n\n"
        f"Send /cancel to abort"
    )
    
    await callback.message.answer(text)
    await state.set_state(CreativeSubmission.waiting_for_content)
    await callback.answer("Send your ad text now")


@router.message(StateFilter(CreativeSubmission.waiting_for_content))
async def process_creative_content(message: Message, state: FSMContext):
    """Process ad text content"""
    if message.text and message.text.startswith("/cancel"):
        await message.answer("Creative submission cancelled")
        await state.clear()
        return
    
    if not message.text:
        await message.answer("Please send text for your ad")
        return
    
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Save content to state
    await state.update_data(creative_content=message.text)
    
    logger.info(f"Creative content received for order {order_id}")
    
    text = (
        f"Ad Text Received\n\n"
        f"Step 2: Send an image or video (optional)\n\n"
        f"Send a photo or video for your ad\n"
        f"Or send /skip to submit without media\n"
        f"Send /cancel to abort"
    )
    
    await message.answer(text)
    await state.set_state(CreativeSubmission.waiting_for_media)


@router.message(StateFilter(CreativeSubmission.waiting_for_media))
async def process_creative_media(message: Message, state: FSMContext):
    """Process ad media (photo or video)"""
    data = await state.get_data()
    order_id = data.get('order_id')
    creative_content = data.get('creative_content')
    
    if message.text:
        if message.text.startswith("/cancel"):
            await message.answer("Creative submission cancelled")
            await state.clear()
            return
        elif message.text.startswith("/skip"):
            # Submit without media
            creative_media_id = None
        else:
            await message.answer("Please send a photo or video, or /skip")
            return
    elif message.photo:
        # Get the largest photo
        creative_media_id = message.photo[-1].file_id
        logger.info(f"Photo received for order {order_id}: {creative_media_id}")
    elif message.video:
        creative_media_id = message.video.file_id
        logger.info(f"Video received for order {order_id}: {creative_media_id}")
    else:
        await message.answer("Please send a photo or video, or /skip")
        return
    
    # Update order with creative
    result = await api_request(
        "PATCH", f"/orders/{order_id}",
        json={
            "creative_content": creative_content,
            "creative_media_id": creative_media_id,
            "status": "creative_submitted"
        }
    )
    
    if "error" in result:
        await message.answer(f"Failed to submit creative - {result.get('error')}")
    else:
        text = (
            f"CREATIVE SUBMITTED SUCCESSFULLY\n\n"
            f"Order ID {order_id}\n"
            f"Status Waiting for approval\n\n"
            f"The channel owner will review your creative\n"
            f"You will be notified when it is approved"
        )
        await message.answer(text)
        await message.answer("SUCCESS - Creative submitted - Channel owner will review it")
        
        logger.info(f"Creative submitted for order {order_id}")
    
    await state.clear()


# ============================================================================
# PENDING ORDERS (CHANNEL OWNER) - PHASE 3 NEW
# ============================================================================

@router.callback_query(F.data == "pending_orders")
async def callback_pending_orders(callback: CallbackQuery):
    """Show pending orders for channel owner to approve"""
    logger.info(f"pending_orders from {callback.from_user.id}")
    
    # Get user's channels
    channels = await api_request("GET", f"/channels/owner/{callback.from_user.id}")
    
    if "error" in channels or not channels:
        await callback.message.answer("You have no channels - Add a channel first")
        await callback.answer()
        return
    
    # Get channel IDs
    channel_ids = [ch['id'] for ch in channels]
    
    # Get all orders for these channels with creative_submitted status
    all_orders = []
    for channel_id in channel_ids:
        orders = await api_request("GET", f"/orders/channel/{channel_id}")
        if "error" not in orders and orders:
            # Filter for creative_submitted status
            pending = [o for o in orders if o.get('status') == 'creative_submitted']
            all_orders.extend(pending)
    
    if not all_orders:
        text = "Pending Orders\n\nNo pending orders to review"
        keyboard = [[InlineKeyboardButton(text="Main Menu", callback_data="main_menu")]]
    else:
        text = f"Pending Orders ({len(all_orders)} total)\n\nOrders waiting for your approval:\n\n"
        
        keyboard = []
        
        for order in all_orders[:5]:
            text += f"Order {order['id']} - {order['ad_type'].capitalize()}\n"
            text += f"Price {order['price']} USD\n"
            text += f"Status Creative Submitted\n\n"
            
            keyboard.append([InlineKeyboardButton(
                text=f"Review Order {order['id']}",
                callback_data=f"review_order_{order['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="Main Menu", callback_data="main_menu")])
    
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await callback.answer()


@router.callback_query(F.data.startswith("review_order_"))
async def callback_review_order(callback: CallbackQuery):
    """Review and approve/reject order creative"""
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Reviewing order {order_id}")
    
    # Get order details
    result = await api_request("GET", f"/orders/{order_id}")
    
    if "error" in result:
        await callback.answer("Order not found", show_alert=True)
        return
    
    order = result
    
    text = (
        f"Review Order {order_id}\n\n"
        f"Ad Type {order['ad_type'].capitalize()}\n"
        f"Price {order['price']} USD\n\n"
        f"Ad Text\n{order.get('creative_content', 'No text')}\n\n"
        f"Media {'Yes' if order.get('creative_media_id') else 'No'}\n\n"
        f"Approve or reject this creative?"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="Approve and Post", callback_data=f"approve_order_{order_id}")],
        [InlineKeyboardButton(text="Reject", callback_data=f"reject_order_{order_id}")],
        [InlineKeyboardButton(text="Back", callback_data="pending_orders")]
    ]
    
    # If there's media, send it first
    if order.get('creative_media_id'):
        try:
            await callback.message.answer_photo(
                photo=order['creative_media_id'],
                caption="Attached media for review"
            )
        except:
            pass
    
    try:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        safe_text = f"Review Order {order_id} - {order['ad_type']} - {order['price']} USD"
        await callback.message.answer(safe_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await callback.answer()


@router.callback_query(F.data.startswith("approve_order_"))
async def callback_approve_order(callback: CallbackQuery):
    """Approve order and post ad to channel"""
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Approving order {order_id}")
    
    # Get order details
    order_result = await api_request("GET", f"/orders/{order_id}")
    
    if "error" in order_result:
        await callback.answer("Order not found", show_alert=True)
        return
    
    order = order_result
    channel_id = order['channel_id']
    
    # Get channel details
    channel_result = await api_request("GET", f"/channels/{channel_id}")
    
    if "error" in channel_result:
        await callback.answer("Channel not found", show_alert=True)
        return
    
    channel = channel_result
    telegram_channel_id = channel['telegram_channel_id']
    
    # Post ad to channel
    try:
        bot = callback.bot
        creative_content = order.get('creative_content', 'Advertisement')
        creative_media_id = order.get('creative_media_id')
        
        if creative_media_id:
            # Post with media
            sent_message = await bot.send_photo(
                chat_id=telegram_channel_id,
                photo=creative_media_id,
                caption=creative_content
            )
        else:
            # Post text only
            sent_message = await bot.send_message(
                chat_id=telegram_channel_id,
                text=creative_content
            )
        
        # Get post URL
        if channel.get('channel_username'):
            post_url = f"https://t.me/{channel['channel_username']}/{sent_message.message_id}"
        else:
            post_url = f"Posted to channel {channel['channel_title']}"
        
        logger.info(f"Ad posted for order {order_id}: {post_url}")
        
        # Update order status
        await api_request(
            "PATCH", f"/orders/{order_id}",
            json={
                "status": "posted",
                "post_url": post_url,
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        
        await callback.message.answer(f"SUCCESS - Ad posted to channel successfully")
        await callback.message.answer(f"Order {order_id} completed\nPost URL: {post_url}")
        
    except Exception as e:
        logger.error(f"Failed to post ad: {e}")
        await callback.message.answer(f"FAILED - Could not post ad: {str(e)}")
    
    await callback.answer()


@router.callback_query(F.data.startswith("reject_order_"))
async def callback_reject_order(callback: CallbackQuery):
    """Reject order creative"""
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Rejecting order {order_id}")
    
    # Update order status back to paid so user can resubmit
    result = await api_request(
        "PATCH", f"/orders/{order_id}",
        json={"status": "paid"}
    )
    
    if "error" in result:
        await callback.answer("Failed to reject order", show_alert=True)
    else:
        await callback.message.answer(f"Order {order_id} rejected - Advertiser can resubmit creative")
        await callback.answer("Order rejected")
    


# ============================================================================
# VIEW ORDER DETAILS
# ============================================================================

@router.callback_query(F.data.startswith("view_order_"))
async def callback_view_order(callback: CallbackQuery):
    """View order details"""
    order_id = int(callback.data.split("_")[-1])
    
    result = await api_request("GET", f"/orders/{order_id}")
    
    if "error" in result:
        await callback.answer("Order not found", show_alert=True)
        return
    
    order = result
    
    status_text = {
        "pending_payment": "Pending Payment",
        "paid": "Paid - Awaiting Creative",
        "creative_submitted": "Creative Submitted - Under Review",
        "posted": "Posted to Channel",
        "completed": "Completed",
        "cancelled": "Cancelled"
    }.get(order['status'], order['status'])
    
    text = (
        f"Order Details\n\n"
        f"Order ID {order['id']}\n"
        f"Ad Type {order['ad_type'].capitalize()}\n"
        f"Price {order['price']} USD\n"
        f"Status {status_text}\n\n"
    )
    
    if order.get('creative_content'):
        text += f"Ad Text\n{order['creative_content']}\n\n"
    
    if order.get('post_url'):
        text += f"Post URL {order['post_url']}\n\n"
    
    if order.get('payment_transaction_id'):
        text += f"Transaction {order['payment_transaction_id']}\n"
    
    keyboard = [[InlineKeyboardButton(text="My Orders", callback_data="my_orders")]]
    
    try:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        safe_text = f"Order {order['id']} - Status {status_text}"
        await callback.message.answer(safe_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await callback.answer()


# ============================================================================
# ORDER CANCELLATION - PHASE 4 NEW
# ============================================================================

@router.callback_query(F.data.startswith("cancel_order_"))
async def callback_cancel_order(callback: CallbackQuery):
    """Cancel an unpaid order"""
    order_id = int(callback.data.split("_")[-1])
    
    logger.info(f"Cancelling order {order_id}")
    
    # Update order status
    result = await api_request(
        "PATCH", f"/orders/{order_id}",
        json={"status": "cancelled"}
    )
    
    if "error" in result:
        await callback.answer("Failed to cancel order", show_alert=True)
    else:
        await callback.message.answer(f"Order {order_id} cancelled successfully")
        await callback.answer("Order cancelled")
        
        logger.info(f"Order {order_id} cancelled")


# ============================================================================
# MAIN MENU
# ============================================================================

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu"""
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
    
    text = "Main Menu\n\nWhat would you like to do?"
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()


def setup_handlers(dp):
    """Register handlers"""
    dp.include_router(router)
    logger.info("Router registered with dispatcher")
    logger.info("Registered handlers with PHASE 4: FINAL PRODUCTION POLISH")
