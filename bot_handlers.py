"""
Telegram Bot Handlers - ULTRA SIMPLE (NO DATABASE REQUIRED)
This version works completely standalone without any API calls
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()

class ChannelRegistration(StatesGroup):
    waiting_for_forward = State()
    waiting_for_pricing = State()

def create_main_menu():
    keyboard = [
        [InlineKeyboardButton(text="📢 I'm a Channel Owner", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🎯 I'm an Advertiser", callback_data="role_advertiser")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_channel_owner_menu():
    keyboard = [
        [InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="🔄 I also want to Advertise", callback_data="role_advertiser")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_advertiser_menu():
    keyboard = [
        [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="🛒 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔄 I also have a Channel", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def check_bot_admin_status(message: Message, channel_id: int) -> dict:
    """Check if bot is admin in the channel"""
    try:
        bot = message.bot
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        
        logger.info(f"📊 Bot status in channel {channel_id}: {bot_member.status}")
        
        is_admin = bot_member.status in ["administrator", "creator"]
        can_post = False
        
        if bot_member.status == "creator":
            can_post = True
        elif bot_member.status == "administrator":
            can_post = getattr(bot_member, 'can_post_messages', False)
        
        return {"is_admin": is_admin, "can_post": can_post}
    except Exception as e:
        logger.error(f"❌ Admin check error: {e}")
        return {"is_admin": False, "can_post": False}

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    logger.info(f"👤 /start from user {message.from_user.id}")
    await state.clear()
    
    welcome_text = (
        "👋 Welcome to Telegram Ads Marketplace!\n\n"
        "Connect channel owners with advertisers.\n\n"
        "👤 Your Profile:\n"
        f"Name: {message.from_user.first_name or 'User'}\n"
        f"Username: @{message.from_user.username or 'Not set'}\n\n"
        "How would you like to use the marketplace?"
    )
    
    await message.answer(welcome_text, reply_markup=create_main_menu())

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
    """Handle /stats command"""
    stats_text = (
        "📊 Statistics\n\n"
        "👥 Users: 0\n"
        "📢 Channels: 0\n"
        "💼 Orders: 0\n"
        "🔥 Active: 0"
    )
    await message.answer(stats_text)

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    """Handle channel owner role selection"""
    logger.info(f"📞 role_channel_owner from {callback.from_user.id}")
    
    text = "📢 Channel Owner Menu\n\nList your channels and earn money!"
    await callback.message.edit_text(text, reply_markup=create_channel_owner_menu())
    await callback.answer()

@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    """Handle advertiser role selection"""
    logger.info(f"📞 role_advertiser from {callback.from_user.id}")
    
    text = "🎯 Advertiser Menu\n\nFind channels for your ads!"
    await callback.message.edit_text(text, reply_markup=create_advertiser_menu())
    await callback.answer()

@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    """Start channel registration"""
    logger.info(f"📞 add_channel from {callback.from_user.id}")
    
    try:
        await state.clear()
        
        text = (
            "📢 Add Your Channel\n\n"
            "Steps:\n"
            "1. Add @trust_ad_marketplace_bot as Administrator\n"
            "2. Enable Post Messages permission\n"
            "3. Forward any message from your channel here\n\n"
            "Ready? Forward a message now!"
        )
        
        await callback.message.edit_text(text)
        await state.set_state(ChannelRegistration.waiting_for_forward)
        await callback.answer("✅ Ready!")
        
        logger.info(f"✅ add_channel completed")
        
    except Exception as e:
        logger.error(f"❌ Error in add_channel: {e}", exc_info=True)
        await callback.answer("⚠️ Error. Try /start", show_alert=True)

@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded channel message"""
    logger.info(f"📨 Channel forward from {message.from_user.id}")
    
    try:
        if not message.forward_from_chat or message.forward_from_chat.type != "channel":
            await message.answer("❌ Please forward a message FROM a Telegram channel.")
            return
        
        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title or "Unknown Channel"
        channel_username = message.forward_from_chat.username
        
        logger.info(f"📢 Channel: {channel_title} ({channel_id})")
        
        # Check admin status
        admin_check = await check_bot_admin_status(message, channel_id)
        
        if not admin_check["is_admin"]:
            text = (
                f"❌ Bot Not Admin\n\n"
                f"I'm not admin in {channel_title}!\n\n"
                f"Fix:\n"
                f"1. Open {channel_title}\n"
                f"2. Settings → Administrators\n"
                f"3. Add @trust_ad_marketplace_bot\n"
                f"4. Enable Post Messages\n"
                f"5. Try again"
            )
            await message.answer(text)
            await state.clear()
            return
        
        if not admin_check["can_post"]:
            text = (
                f"⚠️ No Post Permission\n\n"
                f"I'm admin but can't post in {channel_title}!\n\n"
                f"Fix:\n"
                f"1. {channel_title} → Administrators\n"
                f"2. Tap @trust_ad_marketplace_bot\n"
                f"3. Enable Post Messages\n"
                f"4. Try again"
            )
            await message.answer(text)
            await state.clear()
            return
        
        # SUCCESS - Save to state
        await state.update_data(
            channel_id=channel_id,
            channel_title=channel_title,
            channel_username=channel_username
        )
        
        text = (
            f"✅ Channel Verified!\n\n"
            f"📢 {channel_title}\n"
            f"🔗 @{channel_username or 'Private'}\n\n"
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
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer("❌ Error. Try again.")
        await state.clear()

@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    """Process pricing"""
    try:
        data = await state.get_data()
        if not data:
            await message.answer("❌ No channel data. Start with /start")
            await state.clear()
            return
        
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
        
        pricing_str = "\n".join([f"• {k}: ${v}" for k, v in pricing.items()])
        
        text = (
            f"🎉 Channel Listed!\n\n"
            f"📢 {data['channel_title']}\n"
            f"💰 Pricing:\n{pricing_str}\n\n"
            f"✅ In marketplace!\n"
            f"(Data stored in memory only)"
        )
        
        await message.answer(text)
        await state.clear()
        
        logger.info(f"✅ Registered: {data['channel_title']}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer("❌ Error. Try again.")
        await state.clear()

@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """My channels"""
    text = "📊 My Channels\n\nFeature coming soon!"
    await callback.message.edit_text(text)
    await callback.answer()

@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    """Browse channels"""
    text = "🔍 Browse Channels\n\nFeature coming soon!"
    await callback.message.edit_text(text)
    await callback.answer()

@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """My orders"""
    text = "🛒 My Orders\n\nFeature coming soon!"
    await callback.message.edit_text(text)
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Main menu"""
    await state.clear()
    text = "🏠 Main Menu\n\nWhat would you like to do?"
    await callback.message.edit_text(text, reply_markup=create_main_menu())
    await callback.answer()

def setup_handlers(dp):
    """Register handlers"""
    dp.include_router(router)
    logger.info("✅ Router registered with dispatcher")
    logger.info("📝 Registered handlers:")
    logger.info("  - Commands: /start, /help, /stats")
    logger.info("  - Callbacks: role_channel_owner, role_advertiser, add_channel, browse_channels")
    logger.info("  - Callbacks: purchase, confirm_purchase, my_orders")
    logger.info("  - FSM: ChannelRegistration, PurchaseFlow states")
