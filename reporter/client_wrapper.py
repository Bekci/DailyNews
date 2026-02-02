import asyncio
import logging
import streamlit as st

from client import (
    fetch_available_dates_async,
    fetch_conversations_async,
    submit_selected_date_async,
    fetch_messages_async,
    start_chat_async,
    send_chat_message_async
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
@st.cache_data(ttl=3600)
def fetch_available_dates():
    """Fetch available dates from the API (with caching)"""
    try:
        return asyncio.run(fetch_available_dates_async())
    except Exception as e:
        logger.error(f"Error fetching available dates: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_conversations():
    """Fetch available conversations from the API (with caching)"""
    try:
        return asyncio.run(fetch_conversations_async())
    except Exception as e:
        logger.error(f"Error fetching available conversations: {e}")
        return []

def submit_selected_date(selected_date):
    """Send the selected date to the API"""
    try:
        return asyncio.run(submit_selected_date_async(selected_date))
    except Exception as e:
        logger.error(f"Error fetching available conversations: {e}")
        return None


def fetch_messages(conversation_id: str):
    """Fetch messages for a conversation"""
    try:
        return asyncio.run(fetch_messages_async(conversation_id))
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def start_chat(message: str):
    """Start a new chat conversation"""
    try:
        return asyncio.run(start_chat_async(message))
    except Exception as e:
        logger.error(f"Error starting chat: {e}")
        return None


def send_chat_message(conversation_id: str, message: str):
    """Send a message to the chat"""
    try:
        return asyncio.run(send_chat_message_async(conversation_id, message))
    except Exception as e:
        logger.error(f"Error sending chat message: {e}")
        return None