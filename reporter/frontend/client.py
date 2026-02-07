import os
import aiohttp
import logging

from dotenv import load_dotenv
from datetime import datetime
from typing import Optional
load_dotenv()

API_BASE_URL = os.environ.get("API_BASE_URL")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnauthorizedException(Exception):
    """Raised when API returns 401 Unauthorized"""
    pass


def get_auth_headers(token: Optional[str] = None) -> dict:
    """Get authorization headers if token is provided"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def fetch_available_dates_async(token: Optional[str] = None):
    """Fetch available dates from the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE_URL}/download-options",
                headers=get_auth_headers(token)
            ) as response:
                if response.status == 401:
                    raise UnauthorizedException("Invalid or expired token")
                response.raise_for_status()
                dates = await response.json()
                # Convert string dates to datetime objects if needed
                return sorted([datetime.strptime(d, "%Y-%m-%d") if isinstance(d, str) else d for d in dates])
    except UnauthorizedException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch available dates: {e}")
        return []


async def fetch_conversations_async(token: Optional[str] = None):
    """Fetch conversations from the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE_URL}/conversations",
                headers=get_auth_headers(token)
            ) as response:
                if response.status == 401:
                    raise UnauthorizedException("Invalid or expired token")
                response.raise_for_status()
                data = await response.json()
                return data.get("conversations", [])
    except UnauthorizedException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch conversations: {e}")
        return []


async def submit_selected_date_async(selected_date, token: Optional[str] = None):
    """Send the selected date to the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/download",
                json={"date_str": selected_date.strftime("%Y-%m-%d")},
                headers=get_auth_headers(token)
            ) as response:
                if response.status == 401:
                    raise UnauthorizedException("Invalid or expired token")
                response.raise_for_status()
                return await response.json()
    except UnauthorizedException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Failed to submit date: {e}")
        return None


async def fetch_messages_async(conversation_id: str, token: Optional[str] = None):
    """Fetch messages for a specific conversation asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE_URL}/messages/{conversation_id}",
                headers=get_auth_headers(token)
            ) as response:
                if response.status == 401:
                    raise UnauthorizedException("Invalid or expired token")
                response.raise_for_status()
                data = await response.json()
                return data.get("messages", [])
    except UnauthorizedException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch messages: {e}")
        return []


async def start_chat_async(message: str, token: Optional[str] = None):
    """Start a new chat conversation asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/startchat",
                json={"message": message},
                headers=get_auth_headers(token)
            ) as response:
                if response.status == 401:
                    raise UnauthorizedException("Invalid or expired token")
                response.raise_for_status()
                return await response.json()
    except UnauthorizedException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Failed to start chat: {e}")
        return None


async def send_chat_message_async(conversation_id: str, message: str, token: Optional[str] = None):
    """Send a message to the chat endpoint asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/chat",
                json={"conversation_id": conversation_id, "message": message},
                headers=get_auth_headers(token)
            ) as response:
                if response.status == 401:
                    raise UnauthorizedException("Invalid or expired token")
                response.raise_for_status()
                return await response.json()
    except UnauthorizedException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Failed to send chat message: {e}")
        return None
    

async def send_login_request_async(password: str):
    """Send a login request to the API asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/login",
                json={"password": password}
            ) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Failed to send login request: {e}")
        return None