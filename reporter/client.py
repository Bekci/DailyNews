import aiohttp
import logging

from datetime import datetime

API_BASE_URL = "http://localhost:8081"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_available_dates_async():
    """Fetch available dates from the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/download-options") as response:
                response.raise_for_status()
                dates = await response.json()
                # Convert string dates to datetime objects if needed
                return sorted([datetime.strptime(d, "%Y-%m-%d") if isinstance(d, str) else d for d in dates])
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch available dates: {e}")
        return []


async def fetch_conversations_async():
    """Fetch conversations from the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/conversations") as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("conversations", [])
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch conversations: {e}")
        return []


async def submit_selected_date_async(selected_date):
    """Send the selected date to the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/download",
                json={"date_str": selected_date.strftime("%Y-%m-%d")}
            ) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Failed to submit date: {e}")
        return None


async def fetch_messages_async(conversation_id: str):
    """Fetch messages for a specific conversation asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/messages/{conversation_id}") as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("messages", [])
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch messages: {e}")
        return []


async def start_chat_async(message: str):
    """Start a new chat conversation asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/startchat",
                json={"message": message}
            ) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Failed to start chat: {e}")
        return None


async def send_chat_message_async(conversation_id: str, message: str):
    """Send a message to the chat endpoint asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/chat",
                json={"conversation_id": conversation_id, "message": message}
            ) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Failed to send chat message: {e}")
        return None