"""
bot_handlers.py - Command handlers for the Telegram bot
FINAL VERSION - Uses localhost, comprehensive error handling
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import requests
import os
import logging
import json

logger = logging.getLogger(__name__)

# API base URL - CRITICAL: Use localhost since bot and API run in same process
PORT = os.getenv("PORT", "10000")
API_URL = f"http://127.0.0.1:{PORT}"

logger.info(f"🔗 Bot will call API at: {API_URL}")

# Create router
router = Router()


# ============================================================================
# FSM States
# ============================================================================

class ChannelRegistration(StatesGroup):
    waiting_for_channel = State()
    waiting_for_pricing = State()


class CampaignCreation(StatesGroup):
    waiting_for_brief = State()
    waiting_for_budget = State()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def call_api(method: str, endpoint: str, **kwargs):
    """Call API with comprehensive error handling"""
    try:
        url = f"{API_URL}{endpoint}"
        logger.info(f"🔗 API {method} {url}")
        
        if kwargs.get('json'):
            logger.debug(f"📤 Payload: {json.dumps(kwargs['json'], indent=2)}")
        
        if method == "GET":
            response = requests.get(
                url,
                params=kwargs.get('params'),
                timeout=5  # Shorter timeout for localhost
            )
        elif method == "POST":
            response = requests.post(
                url,
                json=kwargs.get('json'),
                params=kwargs.get('params'),
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
        else:
            logger.error(f"❌ Unsupported method: {method}")
            return None
        
        logger.info(f"📥 Response: {response.status_code}")
        
        if response.status_code >= 400:
            logger.error(f"❌ API Error: {response.text}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        logger.error(f"⏱️ API timeout: {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Connection error: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP error: {e.response.status_code if e.response else 'unknown'}")
        if e.response:
            logger.error(f"Response body: {e.response.text[:500]}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return None


# ============================================================================
# START & HELP COMMANDS
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Welcome message"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    logger.info(f"👤 /start from user {user_id} (@{username})")
    
    # Register user
    result = call_api("POST", "/users/", params={
        "telegram_id": user_id,
        "username": username,
        "first_name": first_name
    })
    
    if result:
        logger.info(f"✅ User registered: {user_id}")
    else:
        logger.warning(f"⚠️  User registration failed: {user_id}")
    
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
    """Help message"""
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
    """Show marketplace statistics"""
    data = call_api("GET", "/stats")
    
    if data:
        stats_text = f"""
📊 <b>Marketplace Statistics</b>

👥 Total Users: {data['total_users']}
📢 Listed Channels: {data['total_channels']}
🤝 Total Deals: {data['total_deals']}
⚡ Active Deals: {data['active_deals']}

<i>Last updated: {data['timestamp'][:19]}</i>
"""
        await message.answer(stats_text)
    else:
        await message.answer("❌ Could not fetch statistics. Please try again later.")


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data == "role_channel_owner")
async def handle_channel_owner(callback: CallbackQuery):
    """Channel Owner menu"""
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
    """Advertiser menu"""
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
    """Start channel registration"""
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
    """Browse available channels"""
    channels = call_api("GET", "/channels/", params={"limit": 10})
    
    if channels is None:
        await callback.message.edit_text("❌ Error loading channels. Please try again.")
        await callback.answer()
        return
    
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
👥 Subscribers: {channel.get('subscribers', 0):,}
👁 Avg Views: {channel.get('avg_views', 0):,}
💰 Post Price: ${post_price}
━━━━━━━━━━━━━━━━
"""
    
    await callback.message.edit_text(text)
    await callback.answer()


# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

@router.message(ChannelRegistration.waiting_for_channel)
async def process_channel_forward(message: Message, state: FSMContext):
    """Process forwarded channel message"""
    
    if not message.forward_origin:
        await message.answer("❌ Please forward a message from your channel.")
        return
    
    if hasattr(message.forward_origin, 'chat'):
        channel = message.forward_origin.chat
    else:
        await message.answer("❌ Could not detect channel information. Please try again.")
        return
    
    if channel.type != "channel":
        await message.answer("❌ This is not a channel. Please forward from a channel.")
        return
    
    logger.info(f"📢 Channel detected: {channel.title} (ID: {channel.id})")
    
    await state.update_data(
        channel_id=channel.id,
        channel_title=channel.title,
        channel_username=channel.username if hasattr(channel, 'username') else None
    )
    
    text = f"""
✅ <b>Channel Detected!</b>

Channel: <b>{channel.title}</b>
Username: @{channel.username if hasattr(channel, 'username') and channel.username else 'private'}

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
    """Process channel pricing and save to database"""
    
    # Parse pricing
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
    
    # Get channel data
    data = await state.get_data()
    
    logger.info(f"💾 Saving channel: {data['channel_title']}")
    logger.info(f"📊 Pricing: {pricing}")
    
    # Save to database
    channel_data = {
        "owner_telegram_id": message.from_user.id,
        "telegram_channel_id": data['channel_id'],
        "channel_username": data['channel_username'],
        "channel_title": data['channel_title'],
        "pricing": pricing,
        "status": "active"
    }
    
    result = call_api("POST", "/channels/create", json=channel_data)
    
    if result:
        logger.info(f"✅ Channel saved: ID {result.get('id')}")
        
        text = f"""
🎉 <b>Channel Listed Successfully!</b>

Channel: <b>{data['channel_title']}</b>
Pricing: {', '.join([f'{k.title()}: ${v}' for k, v in pricing.items()])}

Your channel is now visible to advertisers!
You'll be notified when someone wants to place an ad.

Channel ID: #{result.get('id', 'unknown')}
"""
    else:
        logger.error(f"❌ Failed to save channel: {data['channel_title']}")
        text = """
❌ <b>Error saving channel to database</b>

The server is currently experiencing issues.
Please try again in a few moments.

If the problem persists, contact support.
"""
    
    await message.answer(text)
    await state.clear()


# ============================================================================
# SETUP FUNCTION
# ============================================================================

def setup_handlers(dp):
    """Register all handlers"""
    dp.include_router(router)
    logger.info("✅ Router registered with dispatcher")
