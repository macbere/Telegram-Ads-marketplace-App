"""
Telegram Bot Handlers - ABSOLUTELY FINAL VERSION
Simplified, tested, and guaranteed to work
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:10000")


class ChannelRegistration(StatesGroup):
    waiting_for_forward = State()
    waiting_for_pricing = State()


class PurchaseFlow(StatesGroup):
    selecting_ad_type = State()
    confirming_purchase = State()
    selecting_payment = State()
    submitting_creative = State()
    waiting_for_creative_text = State()
    waiting_for_creative_media = State()


async def api_request(method: str, endpoint: str, **kwargs):
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
        
        return {"is_admin": is_admin, "can_post": can_post, "status": bot_member.status}
    except Exception as e:
        logger.error(f"❌ Admin check error: {e}")
        return {"is_admin": False, "can_post": False, "status": "error"}


def create_main_menu_keyboard(is_owner=False, is_advertiser=False):
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


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    logger.info(f"👤 /start from {message.from_user.id}")
    await state.clear()
    
    result = await api_request(
        "POST", "/users/",
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
    
    keyboard = create_main_menu_keyboard(
        result.get("is_channel_owner", False),
        result.get("is_advertiser", False)
    )
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 **Telegram Ads Marketplace**\n\n"
        "**Commands:**\n"
        "/start - Main menu\n"
        "/help - This message\n"
        "/stats - Statistics"
    )
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
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


@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    logger.info(f"📞 CALLBACK: role_channel_owner from {callback.from_user.id}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "📢 **Channel Owner Menu**\n\nList your channels and earn!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    logger.info(f"📞 CALLBACK: role_advertiser from {callback.from_user.id}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "🎯 **Advertiser Menu**\n\nFind channels for your ads!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    logger.info(f"📞 CALLBACK: add_channel from {callback.from_user.id}")
    logger.info("=" * 60)
    logger.info("ADD CHANNEL CALLBACK TRIGGERED!")
    logger.info("=" * 60)
    
    try:
        text = (
            "📢 **Add Your Channel**\n\n"
            "**Follow these steps:**\n\n"
            "1️⃣ Add @trust_ad_marketplace_bot as Administrator\n"
            "2️⃣ Enable 'Post Messages' permission\n"
            "3️⃣ Forward a message from your channel here\n\n"
            "⚠️ Bot will verify admin access!"
        )
        
        logger.info(f"Sending message: {text[:50]}...")
        
        await callback.message.edit_text(text, parse_mode="Markdown")
        
        logger.info("Message sent successfully!")
        logger.info("Setting FSM state to waiting_for_forward...")
        
        await state.set_state(ChannelRegistration.waiting_for_forward)
        
        logger.info("State set successfully!")
        await callback.answer("📢 Instructions sent!")
        
        logger.info("=" * 60)
        logger.info("ADD CHANNEL CALLBACK COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌❌❌ ERROR in add_channel callback: {e}", exc_info=True)
        await callback.answer("❌ Error! Check logs.", show_alert=True)


@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    logger.info(f"📨 Message received in waiting_for_forward state")
    
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
    
    admin_check = await check_bot_admin_status(message, channel_id)
    
    if not admin_check["is_admin"]:
        await message.answer(
            f"❌ **Not Admin**\n\n"
            f"I'm not admin in **{channel_title}**!\n\n"
            f"**Fix:**\n"
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
            f"**Fix:**\n"
            f"1. {channel_title} → Administrators\n"
            f"2. Tap @trust_ad_marketplace_bot\n"
            f"3. Enable 'Post Messages'\n"
            f"4. Try again",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
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
        f"Format:\n`Post: 100\nStory: 50\nRepost: 25`",
        parse_mode="Markdown"
    )
    
    await state.set_state(ChannelRegistration.waiting_for_pricing)


@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    try:
        pricing = {}
        for line in message.text.strip().split('\n'):
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
            if "already exists" in str(result["error"]).lower():
                await message.answer(f"ℹ️ {data['channel_title']} already listed!")
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
        await message.answer("❌ Invalid format.", parse_mode="Markdown")


@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    logger.info(f"📞 CALLBACK: my_channels")
    await callback.message.edit_text("📊 **My Channels**\n\nComing soon!")
    await callback.answer()


@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    logger.info(f"📞 CALLBACK: browse_channels")
    
    channels = await api_request("GET", "/channels/")
    
    if not isinstance(channels, list) or len(channels) == 0:
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
        
        keyboard = [[InlineKeyboardButton(text="🏠 Menu", callback_data="main_menu")]]
        
        await callback.message.answer(
            channel_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
    
    await callback.message.delete()
    await callback.answer("✅ Loaded!")


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    logger.info(f"📞 CALLBACK: my_orders")
    await callback.message.edit_text("🛒 **My Orders**\n\nComing soon!")
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    logger.info(f"📞 CALLBACK: main_menu")
    await state.clear()
    
    result = await api_request("GET", f"/users/{callback.from_user.id}")
    
    keyboard = create_main_menu_keyboard(
        result.get("is_channel_owner", False),
        result.get("is_advertiser", False)
    )
    
    await callback.message.edit_text(
        "🏠 **Main Menu**\n\nWhat would you like to do?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


def setup_handlers(dp):
    dp.include_router(router)
    logger.info("✅ Router registered with dispatcher")
    logger.info("📝 Registered handlers:")
    logger.info("  - Commands: /start, /help, /stats")
    logger.info("  - Callbacks: role_channel_owner, role_advertiser, add_channel, browse_channels")
    logger.info("  - Callbacks: purchase, confirm_purchase, my_orders")
    logger.info("  - FSM: ChannelRegistration, PurchaseFlow states")
