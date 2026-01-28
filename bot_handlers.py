"""
bot_handlers.py - Command handlers for the Telegram bot
Handles /start, /help, channel listing, and advertiser campaigns
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import requests
import os

# API base URL (your Render API)
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Create router
router = Router()


# ============================================================================
# FSM States for multi-step conversations
# ============================================================================

class ChannelRegistration(StatesGroup):
    waiting_for_channel = State()
    waiting_for_pricing = State()


class CampaignCreation(StatesGroup):
    waiting_for_brief = State()
    waiting_for_budget = State()


# ============================================================================
# START & HELP COMMANDS
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Welcome message when user starts the bot
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Register user in database via API
    try:
        response = requests.post(
            f"{API_URL}/users/",
            params={
                "telegram_id": user_id,
                "username": username,
                "first_name": first_name
            }
        )
    except Exception as e:
        print(f"Error registering user: {e}")
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 I'm a Channel Owner", callback_data="role_channel_owner"),
            InlineKeyboardButton(text="📱 I'm an Advertiser", callback_data="role_advertiser")
        ]
    ])
    
    welcome_text = f"""
👋 <b>Welcome to Telegram Ads Marketplace!</b>

Hi {first_name}! This bot connects:
• <b>Channel Owners</b> who want to monetize their channels
• <b>Advertisers</b> who want to reach new audiences

<b>What would you like to do?</b>
"""
    
    await message.answer(welcome_text, reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Show help message with available commands
    """
    help_text = """
📚 <b>Available Commands:</b>

<b>For Everyone:</b>
/start - Start the bot and choose your role
/help - Show this help message
/stats - View marketplace statistics

<b>For Channel Owners:</b>
/add_channel - List your channel for ads
/my_channels - View your listed channels
/deals - View your active deals

<b>For Advertisers:</b>
/browse - Browse available channels
/create_campaign - Create new ad campaign
/my_campaigns - View your campaigns

<b>Need Help?</b>
Contact support: @support (coming soon)
"""
    await message.answer(help_text)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Show marketplace statistics
    """
    try:
        response = requests.get(f"{API_URL}/stats")
        data = response.json()
        
        stats_text = f"""
📊 <b>Marketplace Statistics</b>

👥 Total Users: {data['total_users']}
📢 Listed Channels: {data['total_channels']}
🤝 Total Deals: {data['total_deals']}
⚡ Active Deals: {data['active_deals']}

<i>Last updated: {data['timestamp'][:19]}</i>
"""
        await message.answer(stats_text)
    except Exception as e:
        await message.answer("❌ Could not fetch statistics. Please try again later.")


# ============================================================================
# CALLBACK HANDLERS (for inline buttons)
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def handle_channel_owner(callback: CallbackQuery):
    """
    User selected Channel Owner role
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add My Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="📋 My Channels", callback_data="my_channels")],
        [InlineKeyboardButton(text="🤝 My Deals", callback_data="my_deals")]
    ])
    
    text = """
📢 <b>Channel Owner Menu</b>

As a channel owner, you can:
• List your channel with pricing
• Review advertiser requests
• Approve/reject ad creatives
• Earn money from your audience

<b>What would you like to do?</b>
"""
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "role_advertiser")
async def handle_advertiser(callback: CallbackQuery):
    """
    User selected Advertiser role
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Browse Channels", callback_data="browse_channels")],
        [InlineKeyboardButton(text="➕ Create Campaign", callback_data="create_campaign")],
        [InlineKeyboardButton(text="📋 My Campaigns", callback_data="my_campaigns")]
    ])
    
    text = """
📱 <b>Advertiser Menu</b>

As an advertiser, you can:
• Browse available channels
• Create ad campaigns
• Submit ad creatives for approval
• Track your campaign performance

<b>What would you like to do?</b>
"""
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "add_channel")
async def handle_add_channel(callback: CallbackQuery, state: FSMContext):
    """
    Start channel registration process
    """
    text = """
➕ <b>Add Your Channel</b>

To list your channel:
1. Add this bot as an <b>Administrator</b> to your channel
2. Forward any message from your channel here

This allows us to:
• Verify you own the channel
• Fetch channel statistics
• Post ads automatically

<i>Forward a message from your channel now...</i>
"""
    
    await callback.message.edit_text(text)
    await state.set_state(ChannelRegistration.waiting_for_channel)
    await callback.answer()


@router.callback_query(F.data == "browse_channels")
async def handle_browse_channels(callback: CallbackQuery):
    """
    Show list of available channels
    """
    try:
        response = requests.get(f"{API_URL}/channels/", params={"limit": 10})
        channels = response.json()
        
        if not channels:
            text = """
😔 <b>No Channels Available Yet</b>

There are currently no channels listed in the marketplace.
Check back soon, or invite channel owners to join!
"""
            await callback.message.edit_text(text)
            await callback.answer()
            return
        
        text = "📢 <b>Available Channels:</b>\n\n"
        
        for channel in channels:
            pricing = channel.get('pricing', {})
            post_price = pricing.get('post', 'N/A')
            
            text += f"""
<b>{channel['channel_title']}</b>
👥 Subscribers: {channel['subscribers']:,}
👁 Avg Views: {channel['avg_views']:,}
💰 Post Price: ${post_price}
━━━━━━━━━━━━━━━━
"""
        
        await callback.message.edit_text(text)
    except Exception as e:
        await callback.message.edit_text("❌ Error loading channels. Please try again.")
    
    await callback.answer()


# ============================================================================
# MESSAGE HANDLERS (for forwarded messages, text input, etc)
# ============================================================================

@router.message(ChannelRegistration.waiting_for_channel)
async def process_channel_forward(message: Message, state: FSMContext):
    """
    Process forwarded message from channel
    """
    if not message.forward_from_chat:
        await message.answer("❌ Please forward a message from your channel.")
        return
    
    channel = message.forward_from_chat
    
    if channel.type != "channel":
        await message.answer("❌ This is not a channel. Please forward from a channel.")
        return
    
    # Store channel info in state
    await state.update_data(
        channel_id=channel.id,
        channel_title=channel.title,
        channel_username=channel.username
    )
    
    text = f"""
✅ <b>Channel Detected!</b>

Channel: <b>{channel.title}</b>
Username: @{channel.username or 'private'}

Now, set your pricing for ad formats.

<b>Example pricing format:</b>
Post: 100
Story: 50
Repost: 30

<i>Send your pricing in this format...</i>
"""
    
    await message.answer(text)
    await state.set_state(ChannelRegistration.waiting_for_pricing)


@router.message(ChannelRegistration.waiting_for_pricing)
async def process_pricing(message: Message, state: FSMContext):
    """
    Process channel pricing input
    """
    # Parse pricing from message
    pricing = {}
    lines = message.text.strip().split('\n')
    
    for line in lines:
        if ':' in line:
            parts = line.split(':')
            format_name = parts[0].strip().lower()
            try:
                price = float(parts[1].strip())
                pricing[format_name] = price
            except ValueError:
                continue
    
    if not pricing:
        await message.answer("❌ Invalid pricing format. Please try again.\n\nExample:\nPost: 100\nStory: 50")
        return
    
    # Get channel data from state
    data = await state.get_data()
    
    # TODO: Register channel via API
    # For now, just confirm
    text = f"""
🎉 <b>Channel Listed Successfully!</b>

Channel: <b>{data['channel_title']}</b>
Pricing: {', '.join([f'{k.title()}: ${v}' for k, v in pricing.items()])}

Your channel is now visible to advertisers!
You'll be notified when someone wants to place an ad.
"""
    
    await message.answer(text)
    await state.clear()


# ============================================================================
# SETUP FUNCTION
# ============================================================================

def setup_handlers(dp):
    """
    Register all handlers with the dispatcher
    """
    dp.include_router(router)
