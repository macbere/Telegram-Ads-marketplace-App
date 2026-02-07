"""
Telegram Bot Handlers
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

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = f"👋 Welcome to Telegram Ads Marketplace!\n\nConnect channel owners with advertisers.\n\n👤 **Your Profile:**\nName: {message.from_user.first_name or 'User'}\nUsername: @{message.from_user.username or 'Not set'}\n\nHow would you like to use the marketplace?"
    await message.answer(welcome_text, reply_markup=create_main_menu(), parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = "🤖 **Telegram Ads Marketplace**\n\n**For Channel Owners:**\n• Add channels\n• Set pricing\n• Earn money\n\n**For Advertisers:**\n• Browse channels\n• Purchase ads\n• Track orders\n\n**Commands:**\n/start - Main menu\n/help - This message\n/stats - Statistics"
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats_text = "📊 **Statistics**\n\n👥 Users: 0\n📢 Channels: 0\n💼 Orders: 0\n🔥 Active: 0"
    await message.answer(stats_text, parse_mode="Markdown")

@router.callback_query(F.data == "role_channel_owner")
async def callback_role_channel_owner(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📢 **Channel Owner Menu**\n\nList your channels and earn money!", reply_markup=create_channel_owner_menu(), parse_mode="Markdown")
        await callback.answer()
    except:
        await callback.answer("✅")

@router.callback_query(F.data == "role_advertiser")
async def callback_role_advertiser(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🎯 **Advertiser Menu**\n\nFind channels for your ads!", reply_markup=create_advertiser_menu(), parse_mode="Markdown")
        await callback.answer()
    except:
        await callback.answer("✅")

@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        await callback.message.edit_text(f"📢 **Add Your Channel**\n\n**Steps:**\n1. Add @{bot_username} as Admin\n2. Enable 'Post Messages' permission\n3. Forward any message from your channel here\n\nReady? Forward a message now!", parse_mode="Markdown")
        await state.set_state(ChannelRegistration.waiting_for_forward)
        await callback.answer("✅ Ready! Forward a message from your channel.")
    except Exception as e:
        logger.error(f"Error in add_channel: {e}")
        await callback.answer("⚠️ Please try again", show_alert=True)

@router.message(StateFilter(ChannelRegistration.waiting_for_forward))
async def process_channel_forward(message: Message, state: FSMContext):
    try:
        if not message.forward_from_chat or message.forward_from_chat.type != "channel":
            await message.answer("❌ Please forward a message FROM a Telegram channel.")
            return
        
        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title or "Unknown Channel"
        channel_username = message.forward_from_chat.username
        
        await state.update_data(channel_id=channel_id, channel_title=channel_title, channel_username=channel_username)
        
        await message.answer(f"✅ **Channel Detected!**\n\n📢 {channel_title}\n🔗 @{channel_username or 'Private channel'}\n\n💰 **Now set your pricing:**\n\nSend pricing in this format:\n`post: 100`\n`story: 50`\n`repost: 25`\n\nExample: Just send `post: 100` for now.", parse_mode="Markdown")
        await state.set_state(ChannelRegistration.waiting_for_pricing)
    except:
        await message.answer("❌ Error processing channel. Please try again.")
        await state.clear()

@router.message(StateFilter(ChannelRegistration.waiting_for_pricing))
async def process_channel_pricing(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        if not data:
            await message.answer("❌ No channel data found. Start over with /start")
            await state.clear()
            return
        
        pricing_text = message.text.strip().lower()
        pricing = {}
        
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
            await message.answer("❌ Invalid format.\n\n**Send like this:**\n`post: 100`\n\nOr:\n`post: 100`\n`story: 50`\n`repost: 25`", parse_mode="Markdown")
            return
        
        pricing_str = "\n".join([f"• {k}: ${v}" for k, v in pricing.items()])
        await message.answer(f"🎉 **Channel Listed Successfully!**\n\n📢 {data['channel_title']}\n💰 Pricing:\n{pricing_str}\n\n✅ Your channel is now in the marketplace!\nAdvertisers can find and purchase ads.", parse_mode="Markdown")
        await state.clear()
    except:
        await message.answer("❌ Error processing pricing. Please try again.")
        await state.clear()

@router.callback_query(F.data == "my_channels")
async def callback_my_channels(callback: CallbackQuery):
    await callback.message.edit_text("📊 **My Channels**\n\nFeature coming soon!", parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "browse_channels")
async def callback_browse_channels(callback: CallbackQuery):
    await callback.message.edit_text("🔍 **Browse Channels**\n\nFeature coming soon!", parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    await callback.message.edit_text("🛒 **My Orders**\n\nFeature coming soon!", parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 **Main Menu**\n\nWhat would you like to do?", reply_markup=create_main_menu(), parse_mode="Markdown")
    await callback.answer()

def setup_handlers(dp):
    dp.include_router(router)
    logger.info("✅ All bot handlers registered successfully")
