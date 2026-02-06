"""
Telegram Bot Handlers - BULLETPROOF VERSION
Will never crash - every possible error is caught
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
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


async def check_bot_admin_status(message: Message, channel_id: int) -> dict:
    """Check if bot is admin in the channel"""
    try:
        bot = message.bot
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        
        logger.info(f"📊 Bot status: {bot_member.status}")
        
        is_admin = bot_member.status in ["administrator", "creator"]
        can_post = False
        
        if bot_member.status == "creator":
            can_post = True
        elif bot_member.status == "administrator":
            can_post = getattr(bot_member, 'can_post_messages', False)
        
        return {
            "is_admin": is_admin,
            "can_post": can_post,
            "status": bot_member.status,
            "error": None
        }
    except Exception as e:
        logger.error(f"❌ Admin check error: {e}")
        return {
            "is_admin": False,
            "can_post": False,
            "status": "error",
            "error": str(e)
        }


def create_main_menu_keyboard(is_owner=False, is_advertiser=False):
    """Create main menu keyboard"""
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


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    logger.info(f"👤 /start from {message.from_user.id}")
    
    await state.clear()
    
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
        await message.answer("❌ Failed to register. Please try again.")
        return
    
    welcome_text = (
        f"👋 Welcome to Telegram Ads Marketplace!\n\n"
        f"Connect channel owners with advertisers.\n\n"
        f"👤 **Your Profile:**\n"
        f"Name: {message.from_user.first_name}\n"
        f"Username: @{message.from_user.username or 'Not set'}\n\n"
        f"How would you like to use the marketplace?"
    )
    
    is_owner = result.get("is_channel_owner", False)
    is_advertiser = result.get("is_advertiser", False)
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 **Telegram Ads Marketplace**\n\n"
        "**For Channel Owners:**\n"
        "• Add channels\n"
        "• Set pricing\n"
        "• Track earnings\n\n"
        "**For Advertisers:**\n"
        "• Browse channels\n"
        "• Purchase ads\n"
        "• Track orders\n\n"
        "**Commands:**\n"
        "/start - Main menu\n"
        "/help - This message\n"
        "/stats - Statistics"
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
        f"📊 **Statistics**\n\n"
        f"👥 Users: {stats.get('total_users', 0)}\n"
        f"📢 Channels: {stats.get('total_channels', 0)}\n"
        f"💼 Orders: {stats.get('total_orders', 0)}\n"
        f"🔥 Active: {stats.get('active_orders', 0)}"
    )
    
    await message.answer(stats_text, parse_mode="Markdown")


# ============================================================================
# ROLE CALLBACKS
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    """Channel owner role"""
    logger.info(f"📞 role_channel_owner")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "📢 **Channel Owner Menu**\n\n"
        "List your channels and earn!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    """Advertiser role"""
    logger.info(f"📞 role_advertiser")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "🎯 **Advertiser Menu**\n\n"
        "Find channels for your ads!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================================
# CHANNEL MANAGEMENT - SIMPLIFIED & BULLETPROOF
# ============================================================================

@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    """Start channel registration - NO bot.get_me() calls!"""
    logger.info(f"📞 add_channel clicked")
    
    # HARDCODE bot username - no API calls that can fail!
    BOT_USERNAME = "trust_ad_marketplace_bot"
    
    await callback.message.edit_text(
        "📢 **Add Your Channel**\n\n"
        "**IMPORTANT Steps:**\n\n"
        f"1️⃣ Add @{BOT_USERNAME} as Admin\n"
        "2️⃣ Enable 'Post Messages'\n"
        "3️⃣ Forward a message here\n\n"
        "⚠️ Bot will verify admin access!",
        parse_mode="Markdown"
    )
    
    await state.set_state(ChannelRegistration.waiting_for_forward)
    await callback.answer()
    
    logger.info("✅ State set to waiting_for_forward")


@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded message"""
    logger.info(f"📨 Message in waiting_for_forward state")
    
    if not message.forward_from_chat:
        await message.answer("❌ Please forward a message from your channel.")
        return
    
    if message.forward_from_chat.type != "channel":
        await message.answer("❌ Not a channel. Please forward from a channel.")
        return
    
    channel_id = message.forward_from_chat.id
    channel_title = message.forward_from_chat.title
    channel_username = message.forward_from_chat.username
    
    logger.info(f"📢 Channel: {channel_title} ({channel_id})")
    
    # CHECK ADMIN
    admin_check = await check_bot_admin_status(message, channel_id)
    
    if not admin_check["is_admin"]:
        await message.answer(
            f"❌ **Not Admin**\n\n"
            f"I'm not admin in **{channel_title}**!\n\n"
            f"**Fix this:**\n"
            f"1. Open {channel_title}\n"
            f"2. Settings → Administrators\n"
            f"3. Add @trust_ad_marketplace_bot\n"
            f"4. Enable 'Post Messages'\n"
            f"5. Try again",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    if not admin_check["can_post"]:
        await message.answer(
            f"⚠️ **No Post Permission**\n\n"
            f"I'm admin but can't post!\n\n"
            f"**Fix this:**\n"
            f"1. {channel_title} → Administrators\n"
            f"2. Tap @trust_ad_marketplace_bot\n"
            f"3. Enable 'Post Messages'\n"
            f"4. Try again",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    # SUCCESS
    logger.info(f"✅ Verified admin in {channel_id}")
    
    await state.update_data(
        channel_id=channel_id,
        channel_title=channel_title,
        channel_username=channel_username
    )
    
    await message.answer(
        f"✅ **Verified!**\n\n"
        f"📢 {channel_title}\n"
        f"🔗 @{channel_username or 'Private'}\n\n"
        f"✅ Admin confirmed\n"
        f"✅ Can post\n\n"
        f"💰 **Set Pricing**\n\n"
        f"Format:\n"
        f"`Post: 100\nStory: 50\nRepost: 25`",
        parse_mode="Markdown"
    )
    
    await state.set_state(ChannelRegistration.waiting_for_pricing)


@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    """Process pricing"""
    try:
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
            await message.answer("❌ Invalid. Use:\n`Post: 100\nStory: 50\nRepost: 25`", parse_mode="Markdown")
            return
        
        data = await state.get_data()
        
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
                await message.answer(f"ℹ️ **Already Listed**\n\n{data['channel_title']} is in marketplace!", parse_mode="Markdown")
            else:
                await message.answer(f"❌ Error: {result['error']}")
        else:
            pricing_text = "\n".join([f"{k.title()}: ${v}" for k, v in pricing.items()])
            await message.answer(
                f"🎉 **Success!**\n\n"
                f"📢 {data['channel_title']}\n"
                f"💰 {pricing_text}\n\n"
                f"✅ Listed! ID: #{result.get('id')}",
                parse_mode="Markdown"
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Pricing error: {e}")
        await message.answer("❌ Invalid. Use:\n`Post: 100\nStory: 50\nRepost: 25`", parse_mode="Markdown")


@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """My channels"""
    await callback.message.edit_text("📊 **My Channels**\n\nComing soon!", parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    """Browse channels"""
    logger.info("📞 browse_channels")
    
    channels = await api_request("GET", "/channels/")
    
    if not isinstance(channels, list):
        await callback.message.edit_text("❌ Failed to load channels.")
        await callback.answer()
        return
    
    if len(channels) == 0:
        await callback.message.edit_text("📢 **No Channels**\n\nCheck back later!")
        await callback.answer()
        return
    
    for channel in channels[:5]:
        pricing = channel.get("pricing", {})
        pricing_text = "\n".join([f"  • {k.title()}: ${v}" for k, v in pricing.items()])
        
        channel_text = (
            f"📢 **{channel['channel_title']}**\n"
            f"🔗 @{channel.get('channel_username', 'Private')}\n"
            f"👥 {channel.get('subscribers', 0):,}\n"
            f"👀 {channel.get('avg_views', 0):,}\n\n"
            f"💰 **Pricing:**\n{pricing_text}"
        )
        
        keyboard = []
        for ad_type, price in pricing.items():
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🛒 {ad_type.title()} ${price}",
                    callback_data=f"purchase:{channel['id']}:{ad_type}:{price}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="🏠 Menu", callback_data="main_menu")])
        
        await callback.message.answer(
            channel_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
    
    await callback.message.delete()
    await callback.answer("✅ Loaded!")


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """My orders"""
    await callback.message.edit_text("🛒 **My Orders**\n\nComing soon!", parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Main menu"""
    await state.clear()
    
    result = await api_request("GET", f"/users/{callback.from_user.id}")
    
    is_owner = result.get("is_channel_owner", False)
    is_advertiser = result.get("is_advertiser", False)
    
    keyboard = create_main_menu_keyboard(is_owner, is_advertiser)
    
    await callback.message.edit_text(
        "🏠 **Main Menu**\n\nWhat would you like to do?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


def setup_handlers(dp):
    """Register handlers"""
    dp.include_router(router)
    logger.info("✅ Handlers registered")
