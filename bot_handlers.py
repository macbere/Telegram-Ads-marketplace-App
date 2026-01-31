"""
bot_handlers.py - Command handlers for the Telegram bot
FINAL FIX: Correct list handling in browse_channels
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import os
import logging
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# API base URL
PORT = os.getenv("PORT", "10000")
API_URL = f"http://127.0.0.1:{PORT}"

logger.info(f"🔗 Bot will call API at: {API_URL}")

# Create router
router = Router()

# Shared aiohttp session
http_session: Optional[aiohttp.ClientSession] = None


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
# ASYNC HTTP CLIENT
# ============================================================================

async def get_http_session() -> aiohttp.ClientSession:
    """Get or create shared HTTP session"""
    global http_session
    if http_session is None or http_session.closed:
        timeout = aiohttp.ClientTimeout(total=30, connect=5, sock_read=10)
        http_session = aiohttp.ClientSession(
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        logger.info("✅ HTTP session created")
    return http_session


async def close_http_session():
    """Close HTTP session on shutdown"""
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()
        logger.info("✅ HTTP session closed")


async def call_api(method: str, endpoint: str, **kwargs):
    """
    Async API caller - returns raw response (could be dict, list, or error dict)
    """
    try:
        url = f"{API_URL}{endpoint}"
        logger.info(f"🔗 API {method} {url}")
        
        session = await get_http_session()
        
        # Prepare request kwargs
        request_kwargs = {}
        if 'json' in kwargs:
            request_kwargs['json'] = kwargs['json']
        if 'params' in kwargs:
            request_kwargs['params'] = kwargs['params']
        
        # Make async request
        async with session.request(method, url, **request_kwargs) as response:
            logger.info(f"📥 Response: {response.status}")
            
            # Parse response body
            try:
                response_data = await response.json()
            except:
                response_data = await response.text()
            
            # Handle errors
            if response.status >= 400:
                error_detail = response_data.get('detail', str(response_data)) if isinstance(response_data, dict) else str(response_data)
                logger.error(f"❌ API Error {response.status}: {error_detail}")
                return {
                    'error': True,
                    'status': response.status,
                    'detail': error_detail
                }
            
            # Return raw response (could be list or dict)
            return response_data
        
    except aiohttp.ClientConnectionError as e:
        logger.error(f"🔌 Connection error: {e}")
        return {'error': True, 'detail': 'Connection error'}
    except aiohttp.ClientTimeout:
        logger.error(f"⏱️ Request timeout: {url}")
        return {'error': True, 'detail': 'Request timeout'}
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return {'error': True, 'detail': str(e)}


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
    result = await call_api("POST", "/users/", params={
        "telegram_id": user_id,
        "username": username,
        "first_name": first_name
    })
    
    if result and not isinstance(result, dict) or not result.get('error'):
        logger.info(f"✅ User registered: {user_id}")
    
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
    data = await call_api("GET", "/stats")
    
    if isinstance(data, dict) and not data.get('error'):
        stats_text = f"""
📊 <b>Marketplace Statistics</b>

👥 Total Users: {data.get('total_users', 0)}
📢 Listed Channels: {data.get('total_channels', 0)}
🤝 Total Deals: {data.get('total_deals', 0)}
⚡ Active Deals: {data.get('active_deals', 0)}

<i>Last updated: {data.get('timestamp', '')[:19]}</i>
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
    logger.info(f"📞 Callback: role_channel_owner from user {callback.from_user.id}")
    
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
    logger.info(f"📞 Callback: role_advertiser from user {callback.from_user.id}")
    
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
    logger.info(f"📞 Callback: add_channel from user {callback.from_user.id}")
    
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
    """Browse available channels - FIXED VERSION"""
    logger.info(f"📞 Callback: browse_channels from user {callback.from_user.id}")
    
    # Call API to get channels
    channels = await call_api("GET", "/channels/", params={"limit": 10})
    
    logger.info(f"🔍 API Response type: {type(channels)}")
    logger.info(f"🔍 API Response: {channels}")
    
    # Check if it's an error dict
    if isinstance(channels, dict) and channels.get('error'):
        logger.error(f"❌ API returned error: {channels.get('detail')}")
        await callback.message.edit_text("❌ Error loading channels. Please try again.")
        await callback.answer()
        return
    
    # Check if it's an empty list or None
    if not channels or (isinstance(channels, list) and len(channels) == 0):
        logger.warning("⚠️ No channels found in database")
        text = """
😔 <b>No Channels Available Yet</b>

There are currently no channels listed in the marketplace.
Check back soon, or invite channel owners to join!
"""
        await callback.message.edit_text(text)
        await callback.answer()
        return
    
    # Channels found! Build the response
    logger.info(f"✅ Found {len(channels)} channels")
    
    text = "📢 <b>Available Channels:</b>\n\n"
    
    for channel in channels:
        logger.info(f"Processing channel: {channel.get('channel_title')}")
        
        pricing = channel.get('pricing', {})
        post_price = pricing.get('post', 'N/A')
        story_price = pricing.get('story', 'N/A')
        repost_price = pricing.get('repost', 'N/A')
        
        text += f"""
<b>{channel.get('channel_title', 'Unknown Channel')}</b>
@{channel.get('channel_username', 'private')}
👥 Subscribers: {channel.get('subscribers', 0):,}
👁 Avg Views: {channel.get('avg_views', 0):,}

💰 <b>Pricing:</b>
  • Post: ${post_price}
  • Story: ${story_price}
  • Repost: ${repost_price}

━━━━━━━━━━━━━━━━
"""
    
    logger.info(f"📝 Sending response with {len(channels)} channels")
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "my_channels")
async def handle_my_channels(callback: CallbackQuery):
    """Show user's channels (placeholder)"""
    logger.info(f"📞 Callback: my_channels from user {callback.from_user.id}")
    
    await callback.message.edit_text("📋 <b>My Channels</b>\n\nThis feature is coming soon!")
    await callback.answer()


@router.callback_query(F.data == "my_deals")
async def handle_my_deals(callback: CallbackQuery):
    """Show user's deals (placeholder)"""
    logger.info(f"📞 Callback: my_deals from user {callback.from_user.id}")
    
    await callback.message.edit_text("🤝 <b>My Deals</b>\n\nThis feature is coming soon!")
    await callback.answer()


@router.callback_query(F.data == "create_campaign")
async def handle_create_campaign(callback: CallbackQuery):
    """Create campaign (placeholder)"""
    logger.info(f"📞 Callback: create_campaign from user {callback.from_user.id}")
    
    await callback.message.edit_text("➕ <b>Create Campaign</b>\n\nThis feature is coming soon!")
    await callback.answer()


@router.callback_query(F.data == "my_campaigns")
async def handle_my_campaigns(callback: CallbackQuery):
    """Show user's campaigns (placeholder)"""
    logger.info(f"📞 Callback: my_campaigns from user {callback.from_user.id}")
    
    await callback.message.edit_text("📋 <b>My Campaigns</b>\n\nThis feature is coming soon!")
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
    
    result = await call_api("POST", "/channels/create", json=channel_data)
    
    # Handle response
    if isinstance(result, dict) and result.get('error'):
        status = result.get('status')
        detail = result.get('detail', 'Unknown error')
        
        if status == 400 and 'already registered' in detail.lower():
            text = f"""
ℹ️ <b>Channel Already Listed</b>

<b>{data['channel_title']}</b> is already in the marketplace!

Your channel is visible to advertisers and you can receive deal requests.

Use /my_channels to view your channels.
"""
        else:
            text = f"""
❌ <b>Error Saving Channel</b>

Reason: {detail}

Please try again or contact support if the issue persists.
"""
    elif isinstance(result, dict) and result.get('id'):
        channel_id = result['id']
        logger.info(f"✅ Channel saved: ID {channel_id}")
        
        text = f"""
🎉 <b>Channel Listed Successfully!</b>

Channel: <b>{data['channel_title']}</b>
Pricing: {', '.join([f'{k.title()}: ${v}' for k, v in pricing.items()])}

Your channel is now visible to advertisers!
You'll be notified when someone wants to place an ad.

Channel ID: #{channel_id}
"""
    else:
        text = """
❌ <b>Server Error</b>

Could not save channel. Please try again.
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
    logger.info("📝 Registered handlers:")
    logger.info("  - Commands: /start, /help, /stats")
    logger.info("  - Callbacks: role_channel_owner, role_advertiser, add_channel, browse_channels")
    logger.info("  - FSM: ChannelRegistration states")


async def shutdown_handlers():
    """Cleanup on shutdown"""
    await close_http_session()
    logger.info("✅ Handlers cleaned up")
