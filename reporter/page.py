import asyncio
import logging
import streamlit as st

from client import fetch_available_dates_async
from client import fetch_conversations_async
from client import submit_selected_date_async
from client import fetch_messages_async
from client import start_chat_async
from client import send_chat_message_async
from  datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATE_VISUAL_FORMAT = "%d %b %Y"
DATE_TIME_VISUAL_FORMAT = "%d %b %Y %H:%M"

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


@st.dialog("Belgeler", width="medium", on_dismiss=lambda: st.session_state.update({"documents_dialog_open": False}))
def show_documents_dialog(documents: list):
    """Display documents in a dialog"""
    st.write("### Kaynak Belgeler")
    for idx, doc in enumerate(documents, 1):
        st.write(f"{idx}. {doc}")


@st.dialog("Haberleri indirmek için bir gün seç")
def show_date_picker_dialog():
    # Fetch available dates on first load or when needed
    if "available_dates" not in st.session_state:
        with st.spinner("Loading available dates..."):
            available_dates = fetch_available_dates()
            if not available_dates:
                st.info("İndirilebilir haber bulunamadı.")
                return

    selected_date = st.selectbox(
        "Hangi tarihin haberlerini indirmek istersiniz?",
        options=available_dates,
        format_func=lambda d: d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d),
        key="date_selector"
    )

    st.session_state.dialog_selected_date = selected_date

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Submit", key="submit_btn"):
            # Send request to API
            st.session_state.download_result = submit_selected_date(selected_date)
            # Close dialog after API response is retrieved
            st.session_state.dialog_open = False
            st.rerun()
    
    with col2:
        if st.button("Cancel", key="cancel_btn"):
            st.session_state.dialog_open = False
            st.rerun()


def render_menu():
    def render_new_conversation_button():
        if st.button("➕ Yeni Konuşma Başlat", key="start_new_conv_btn", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_conversation_id = None
            st.session_state.selected_conversation = None
            st.rerun()

    def render_conversations():
        st.subheader("📋 Konuşmalar")
    
        with st.container(height=800, border=True):
            if st.session_state.conversations_list:
                for conv in st.session_state.conversations_list:
                    # Create a clickable conversation item
                    if st.button(
                        f"📅 {datetime.fromtimestamp(conv['created_at']).strftime(DATE_VISUAL_FORMAT)}\n{conv['first_question'][:40]}...",
                        key=f"conv_{conv['conversation_id']}",
                        use_container_width=True
                    ):
                        st.session_state.selected_conversation = conv['conversation_id']
                        st.rerun()
            else:
                st.info("Henüz Ulak'a bir soru sormadın.")

    def render_download_options():
        if st.button("📩 Haber bültenleri", key="download_btn", use_container_width=True):
            st.session_state.dialog_open = True
        if st.session_state.dialog_open:
            show_date_picker_dialog()
        # Show download button if download_url is available
        if "download_result" in st.session_state:
            result = st.session_state.download_result
            if result and result.get("download_url", None):
                st.link_button(
                    f"📥 {st.session_state.dialog_selected_date.strftime(DATE_VISUAL_FORMAT)} tarihli haberleri indir",
                    result.get("download_url"),
                    use_container_width=True
                )
            else:
                st.error("İndirme linki oluşturulamadı")
    
    render_new_conversation_button()
    st.divider()
    render_conversations()
    st.divider()
    render_download_options()

def render_chat():
    st.title("📰 Ulak'a sor")

    # Initialize session state for messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    if "documents_dialog_open" not in st.session_state:
        st.session_state.documents_dialog_open = False
    if "selected_documents" not in st.session_state:
        st.session_state.selected_documents = None
    
    # Load messages if a conversation is selected
    if st.session_state.selected_conversation and st.session_state.selected_conversation != st.session_state.current_conversation_id:
        with st.spinner("Konuşma yükleniyor..."):
            messages = fetch_messages(st.session_state.selected_conversation)
            st.session_state.messages = messages
            st.session_state.current_conversation_id = st.session_state.selected_conversation
    
    # Display messages
    message_container = st.container()
    with message_container:
        if not st.session_state.messages:
            st.info("💬 Yeni bir konuşmaya başlamak için Ulak'a soru sor.")
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["message"])
                    st.caption(f"⏰ {datetime.fromtimestamp(msg['created_at']).strftime(DATE_TIME_VISUAL_FORMAT)}")
            elif msg["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.write(msg["message"])
                    st.caption(f"⏰ {datetime.fromtimestamp(msg['created_at']).strftime(DATE_TIME_VISUAL_FORMAT)}")
                    
                    # Display documents button if documents exist
                    if msg.get("documents"):
                        if st.button("📄 Belgeleri Göster", key=f"docs_btn_{id(msg)}", use_container_width=False):
                            st.session_state.selected_documents = msg["documents"]
                            st.session_state.documents_dialog_open = True
        
        # Show documents dialog if triggered
        if st.session_state.documents_dialog_open and st.session_state.selected_documents:
            show_documents_dialog(st.session_state.selected_documents)
    
    # Handle message input
    user_input = st.chat_input("Ulak'a soru sor")
    
    if user_input:
        # If no conversation is selected, start a new one
        if not st.session_state.current_conversation_id:
            with st.spinner("Konuşma başlatılıyor..."):
                chat_response = start_chat(user_input)
                if chat_response:
                    st.session_state.current_conversation_id = chat_response["conversation_id"]
                    st.session_state.messages = []
                    st.session_state.selected_conversation = chat_response["conversation_id"]
                    # Add the new conversation to the list
                    st.session_state.conversations_list.insert(0, chat_response)
        
        st.session_state.messages.append({"role": "user", "message": user_input, "created_at": datetime.now().timestamp()})
        
        with st.chat_message("user"):
            st.write(user_input)
            
        # Send the message to the chat endpoint
        if st.session_state.current_conversation_id:
            with st.spinner("Ulak düşünüyor..."):
                agent_response = send_chat_message(st.session_state.current_conversation_id, user_input)
                if agent_response:
                    # Refresh messages from the conversation
                    assistant_message = {
                        "role": "assistant",
                        "message": agent_response["response"],
                        "created_at": datetime.now().timestamp()
                    }
                    # Add documents if available in response
                    if "documents" in agent_response:
                        assistant_message["documents"] = agent_response["documents"]
                    
                    st.session_state.messages.append(assistant_message)
                    st.session_state.user_input = ""
                    st.rerun()

def main():
    st.set_page_config(page_title="Ulak", layout="wide")

    # Initialize session state
    if "dialog_open" not in st.session_state:
        st.session_state.dialog_open = False
    if "selected_conversation" not in st.session_state:
        st.session_state.selected_conversation = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    if "conversations_list" not in st.session_state:
        st.session_state.conversations_list = fetch_conversations()

    with st.sidebar:
        render_menu()
    
    render_chat()

if __name__ == "__main__":
    main()
