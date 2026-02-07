import asyncio
import logging
import streamlit as st

from client import (
    fetch_available_dates_async,
    fetch_conversations_async,
    submit_selected_date_async,
    fetch_messages_async,
    start_chat_async,
    send_chat_message_async,
    send_login_request_async,
    UnauthorizedException
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_token() -> str | None:
    """Get the authentication token from session state"""
    return st.session_state.authentication.get("token") if st.session_state.get("authentication") else None


def clear_authentication():
    """Clear authentication and set error message"""
    st.session_state.authentication["authenticated"] = False
    st.session_state.authentication["token"] = None
    st.session_state.ui["error"] = "Your session has expired. Please log in again."
    logger.warning("Authentication cleared due to unauthorized request")
    
@st.cache_data(ttl=3600)
def fetch_available_dates():
    """Fetch available dates from the API (with caching)"""
    try:
        token = get_token()
        return asyncio.run(fetch_available_dates_async(token=token))
    except UnauthorizedException:
        clear_authentication()
        return []
    except Exception as e:
        logger.error(f"Error fetching available dates: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_conversations():
    """Fetch available conversations from the API (with caching)"""
    try:
        token = get_token()
        return asyncio.run(fetch_conversations_async(token=token))
    except UnauthorizedException:
        clear_authentication()
        return []
    except Exception as e:
        logger.error(f"Error fetching available conversations: {e}")
        return []

def submit_selected_date(selected_date):
    """Send the selected date to the API"""
    try:
        token = get_token()
        return asyncio.run(submit_selected_date_async(selected_date, token=token))
    except UnauthorizedException:
        clear_authentication()
        return None
    except Exception as e:
        logger.error(f"Error fetching available conversations: {e}")
        return None


def fetch_messages(conversation_id: str):
    """Fetch messages for a conversation"""
    try:
        token = get_token()
        return asyncio.run(fetch_messages_async(conversation_id, token=token))
    except UnauthorizedException:
        clear_authentication()
        return []
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def start_chat(message: str):
    """Start a new chat conversation"""
    try:
        token = get_token()
        return asyncio.run(start_chat_async(message, token=token))
    except UnauthorizedException:
        clear_authentication()
        return None
    except Exception as e:
        logger.error(f"Error starting chat: {e}")
        return None


def send_chat_message(conversation_id: str, message: str):
    """Send a message to the chat"""
    try:
        token = get_token()
        return asyncio.run(send_chat_message_async(conversation_id, message, token=token))
    except UnauthorizedException:
        clear_authentication()
        return None
    except Exception as e:
        logger.error(f"Error sending chat message: {e}")
        return None
    
def send_login_request(password: str):
    """Send login request to the API"""
    try:
        return asyncio.run(send_login_request_async(password))
    except Exception as e:
        logger.error(f"Error sending login request: {e}")
        return None