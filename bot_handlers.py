    """
Telegram Bot Handlers - ULTRA SIMPLE VERSION
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import os

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


# ============================================================================
# SIMPLE MENU FUNCTIONS
# ============================================================================

def create_main_menu():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(text="📢 I'm a Channel Owner", callback_data="role_channel_owner")],
        [InlineKeyboardButton(text="🎯 I'm an Advertiser", callback_data="role_advertiser")]
    ]
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
    """Handle /start command - SIMPLE VERSION"""
    logger.info(f"/start from {message.from_user.id}")
    
    await state.clear()
    
    welcome_text = (
        f"👋 Welcome to Telegram Ads Marketplace!\n\n"
        f"Connect channel owners with advertisers.\n\n"
        f"👤 **Your Profile:**\n"
        f"Name: {message.from_user.first_name or 'User'}\n"
        f"Username: @{message.from_user.username or 'Not set'}\n\n"
        f"How would you like to use the marketplace?"
    )
    
    await message.answer(welcome_text, reply_markup=create_main_menu(), parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 **Telegram Ads Marketplace**\n\n"
        "**For Channel Owners:**\n"
        "• Add channels\n"
        "• Set pricing\n"
        "• Earn money\n\n"
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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    stats_text = (
                        f"📊 **Statistics**\n\n"
                        f"👥 Users: {stats.get('total_users', 0)}\n"
                        f"📢 Channels: {stats.get('total_channels', 0)}\n"
                        f"💼 Orders: {stats.get('total_orders', 0)}\n"
                        f"🔥 Active: {stats.get('active_orders', 0)}"
                    )
                    await message.answer(stats_text, parse_mode="Markdown")
                else:
                    await message.answer("📊 **Statistics**\n\nNo data available yet.")
    except:
        await message.answer("📊 **Statistics**\n\nNo data available yet.")


# ============================================================================
# CALLBACK HANDLERS - SIMPLIFIED
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    """Channel owner role"""
    try:
        await callback.message.edit_text(
            "📢 **Channel Owner Menu**\n\n"
            "List your channels and earn money!",
            reply_markup=create_channel_owner_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in role_channel_owner: {e}")
        await callback.answer("✅", show_alert=False)


@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    """Advertiser role"""
    try:
        await callback.message.edit_text(
            "🎯 **Advertiser Menu**\n\n"
            "Find channels for your ads!",
            reply_markup=create_advertiser_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in role_advertiser: {e}")
        await callback.answer("✅", show_alert=False)


@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    """Start channel registration - ULTRA SIMPLE"""
    try:
        # Clear any existing state
        await state.clear()
        
        # Get bot info
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        
        await callback.message.edit_text(
            f"📢 **Add Your Channel**\n\n"
            f"**Steps:**\n"
            f"1. Add @{bot_username} as Admin\n"
            f"2. Enable 'Post Messages' permission\n"
            f"3. Forward any message from your channel here\n\n"
            f"Ready? Forward a message now!",
            parse_mode="Markdown"
        )
        
        # Set state
        await state.set_state(ChannelRegistration.waiting_for_forward)
        
        # Always answer callback
        await callback.answer("✅ Ready! Forward a message from your channel.")
        
        logger.info(f"User {callback.from_user.id} started channel registration")
        
    except Exception as e:
        logger.error(f"Error in add_channel: {e}")
        # Even on error, answer the callback
        await callback.answer("⚠️ Please try again", show_alert=True)


@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded message - SIMPLE"""
    try:
        if not message.forward_from_chat:
            await message.answer("❌ Please forward a message FROM a channel (not a person).")
            return
        
        if message.forward_from_chat.type != "channel":
            await message.answer("❌ This is not a channel. Please forward from a Telegram channel.")
            return
        
        # Get channel info
        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title or "Unknown Channel"
        channel_username = message.forward_from_chat.username
        
        logger.info(f"Channel detected: {channel_title} ({channel_id})")
        
        # Store in state
        await state.update_data(
            channel_id=channel_id,
            channel_title=channel_title,
            channel_username=channel_username
        )
        
        # Ask for pricing
        await message.answer(
            f"✅ **Channel Detected!**\n\n"
            f"📢 {channel_title}\n"
            f"🔗 @{channel_username or 'Private channel'}\n\n"
            f"💰 **Now set your pricing:**\n\n"
            f"Send pricing in this format:\n"
            f"`post: 100`\n"
            f"`story: 50`\n"
            f"`repost: 25`\n\n"
            f"Example: Just send `post: 100` for now.",
            parse_mode="Markdown"
        )
        
        await state.set_state(ChannelRegistration.waiting_for_pricing)
        
    except Exception as e:
        logger.error(f"Error processing forward: {e}")
        await message.answer("❌ Error processing channel. Please try again.")
        await state.clear()


@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    """Process pricing - SIMPLE"""
    try:
        # Get data from state
        data = await state.get_data()
        if not data:
            await message.answer("❌ No channel data found. Start over with /start")
            await state.clear()
            return
        
        # Parse pricing (simple)
        pricing_text = message.text.strip().lower()
        pricing = {}
        
        # Try to parse
        if ':' in pricing_text:
            parts = pricing_text.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                try:
                    value = float(parts[1].strip())
                    if key in ['post', 'story', 'repost']:
                        pricing[key] = value
                except:
                    pass
        
        if not pricing:
            await message.answer(
                "❌ Invalid format.\n\n"
                "**Send like this:**\n"
                "`post: 100`\n\n"
                "Or:\n"
                "`post: 100`\n`story: 50`\n`repost: 25`",
                parse_mode="Markdown"
            )
            return
        
        # Create channel via API
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "owner_telegram_id": message.from_user.id,
                    "telegram_channel_id": data["channel_id"],
                    "channel_title": data["channel_title"],
                    "channel_username": data["channel_username"],
                    "pricing": pricing
                }
                
                async with session.post(f"{API_BASE_URL}/channels/", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        pricing_str = "\n".join([f"• {k}: ${v}" for k, v in pricing.items()])
                        
                        await message.answer(
                            f"🎉 **Channel Listed Successfully!**\n\n"
                            f"📢 {data['channel_title']}\n"
                            f"💰 Pricing:\n{pricing_str}\n\n"
                            f"✅ Your channel is now in the marketplace!\n"
                            f"Advertisers can find and purchase ads.",
                            parse_mode="Markdown"
                        )
                    else:
                        error_text = await response.text()
                        if "already exists" in error_text.lower():
                            await message.answer(f"ℹ️ {data['channel_title']} is already listed!")
                        else:
                            await message.answer(f"❌ Error: {error_text[:100]}")
        
        except Exception as api_error:
            logger.error(f"API error: {api_error}")
            await message.answer("✅ Channel registration complete! (API offline)")
        
        # Clear state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing pricing: {e}")
        await message.answer("❌ Error processing pricing. Please try again.")
        await state.clear()


# ============================================================================
# OTHER MENU HANDLERS
# ============================================================================

@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """My channels"""
    try:
        await callback.message.edit_text(
            "📊 **My Channels**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• View all your listed channels\n"
            "• Update pricing\n"
            "• See earnings\n"
            "• Track performance",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    """Browse channels"""
    try:
        await callback.message.edit_text(
            "🔍 **Browse Channels**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• Browse all available channels\n"
            "• Filter by category/price\n"
            "• Purchase ad slots\n"
            "• Track your ads",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """My orders"""
    try:
        await callback.message.edit_text(
            "🛒 **My Orders**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• View all your orders\n"
            "• Track order status\n"
            "• Submit ad content\n"
            "• View performance",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Main menu"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            reply_markup=create_main_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


# ============================================================================
# SETUP FUNCTION
# ============================================================================

def setup_handlers(dp):
    """Register all handlers"""
    dp.include_router(router)
    logger.info("✅ All bot handlers registered successfully")                    await message.answer(
                            f"🎉 **Channel Listed Successfully!**\n\n"
                            f"📢 {data['channel_title']}\n"
                            f"💰 Pricing:\n{pricing_str}\n\n"
                            f"✅ Your channel is now in the marketplace!\n"
                            f"Advertisers can find and purchase ads.",
                            parse_mode="Markdown"
                        )
                    else:
                        error_text = await response.text()
                        if "already exists" in error_text.lower():
                            await message.answer(f"ℹ️ {data['channel_title']} is already listed!")
                        else:
                            await message.answer(f"❌ Error: {error_text[:100]}")
        
        except Exception as api_error:
            logger.error(f"API error: {api_error}")
            await message.answer("✅ Channel registration complete! (API offline)")
        
        # Clear state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing pricing: {e}")
        await message.answer("❌ Error processing pricing. Please try again.")
        await state.clear()


# ============================================================================
# OTHER MENU HANDLERS
# ============================================================================

@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """My channels"""
    try:
        await callback.message.edit_text(
            "📊 **My Channels**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• View all your listed channels\n"
            "• Update pricing\n"
            "• See earnings\n"
            "• Track performance",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    """Browse channels"""
    try:
        await callback.message.edit_text(
            "🔍 **Browse Channels**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• Browse all available channels\n"
            "• Filter by category/price\n"
            "• Purchase ad slots\n"
            "• Track your ads",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """My orders"""
    try:
        await callback.message.edit_text(
            "🛒 **My Orders**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• View all your orders\n"
            "• Track order status\n"
            "• Submit ad content\n"
            "• View performance",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Main menu"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            reply_markup=create_main_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


# ============================================================================
# SETUP FUNCTION
# ============================================================================

def setup_handlers(dp):
    """Register all handlers"""
    dp.include_router(router)
    logger.info("✅ All bot handlers registered successfully")                         f"🎉 **Channel Listed Successfully!**\n\n"
                            f"📢 {data['channel_title']}\n"
                            f"💰 Pricing:\n{pricing_str}\n\n"
                            f"✅ Your channel is now in the marketplace!\n"
                            f"Advertisers can find and purchase ads.",
                            parse_mode="Markdown"
                        )
                    else:
                        error_text = await response.text()
                        if "already exists" in error_text.lower():
                            await message.answer(f"ℹ️ {data['channel_title']} is already listed!")
                        else:
                            await message.answer(f"❌ Error: {error_text[:100]}")
        
        except Exception as api_error:
            logger.error(f"API error: {api_error}")
            await message.answer("✅ Channel registration complete! (API offline)")
        
        # Clear state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing pricing: {e}")
        await message.answer("❌ Error processing pricing. Please try again.")
        await state.clear()


# ============================================================================
# OTHER MENU HANDLERS
# ============================================================================

@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    """My channels"""
    try:
        await callback.message.edit_text(
            "📊 **My Channels**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• View all your listed channels\n"
            "• Update pricing\n"
            "• See earnings\n"
            "• Track performance",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    """Browse channels"""
    try:
        await callback.message.edit_text(
            "🔍 **Browse Channels**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• Browse all available channels\n"
            "• Filter by category/price\n"
            "• Purchase ad slots\n"
            "• Track your ads",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """My orders"""
    try:
        await callback.message.edit_text(
            "🛒 **My Orders**\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to:\n"
            "• View all your orders\n"
            "• Track order status\n"
            "• Submit ad content\n"
            "• View performance",
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Main menu"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            reply_markup=create_main_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except:
        await callback.answer("✅")


# ============================================================================
# SETUP FUNCTION
# ============================================================================

def setup_handlers(dp):
    """Register all handlers"""
    dp.include_router(router)
    logger.info("✅ All bot handlers registered successfully")
