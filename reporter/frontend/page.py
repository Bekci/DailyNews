import os
import time
import hmac
import streamlit as st
from client_wrapper import (
    fetch_available_dates,
    fetch_conversations,
    send_login_request,
    submit_selected_date,
    fetch_messages,
    start_chat,
    send_chat_message,
    fetch_playback_options,
    fetch_playback
)
from audio_player import render_audio_player
from datetime import datetime

MAX_ATTEMPTS = 5
LOCK_TIME = 300  # seconds (5 min)
DATE_VISUAL_FORMAT = "%d %b %Y"
DATE_TIME_VISUAL_FORMAT = "%d %b %Y %H:%M"

def init_state():

    if "authentication" not in st.session_state:
        st.session_state.authentication = {
            "attempts": 0,
            "locked_until": 0,
            "authenticated": False,
            "token": None
        }


    if "ui" not in st.session_state:
        st.session_state.ui = {
            "document_dialog_open": False,
            "date_dialog_open": False,
            "login_dialog_open": False,
            "error": None
        }

    if "data" not in st.session_state:
        st.session_state.data = {
            "conversations": [],
            "available_dates": [],
            "dialog_selected_date": None,
            "download_result": None,
            "current_documents": []
        }

    if "chat" not in st.session_state:
        reset_chat()

    if "audio" not in st.session_state:
        st.session_state.audio = {
            "language": None,
            "available_dates": [],
            "options_error": False,
            "playback_key": None,
            "playback": None,
        }

def reset_chat():
    st.session_state.chat = {
        "current_conversation_id": None,
        "selected_conversation": None,
        "messages": [],
    }        

def on_authenticated(token):
    st.session_state.authentication["authenticated"] = True
    st.session_state.authentication["attempts"] = 0
    st.session_state.authentication["locked_until"] = 0
    st.session_state.authentication["token"] = token
    # Fetch conversations after successful authentication
    st.session_state.data["conversations"] = fetch_conversations()

def on_authentication_failed():
    st.session_state.authentication["attempts"] += 1
    
    if st.session_state.authentication["attempts"] >= MAX_ATTEMPTS:
        st.session_state.authentication["locked_until"] = time.time() + LOCK_TIME
        return True # Locked
    return False

def close_document_dialog():
    st.session_state.ui["document_dialog_open"] = False

def open_document_dialog():
    st.session_state.ui["document_dialog_open"] = True

def close_date_dialog():
    st.session_state.ui["date_dialog_open"] = False

def open_date_dialog():
    st.session_state.ui["date_dialog_open"] = True

def close_login_dialog():
    st.session_state.ui["login_dialog_open"] = False

def open_login_dialog():
    st.session_state.ui["login_dialog_open"] = True

def on_date_selected(selected_date):
    st.session_state.data["dialog_selected_date"] = selected_date
    # Send request to API for retrieving the download link
    st.session_state.data["download_result"] = submit_selected_date(selected_date)
    close_date_dialog()

def set_error_message(error_message):
    st.session_state.ui.update({"error": error_message})

def is_different_conversation_selected(current_chat):
    return current_chat["selected_conversation"] and current_chat["selected_conversation"] != current_chat["current_conversation_id"]

@st.dialog("Belgeler", width="medium", on_dismiss=close_document_dialog)
def show_documents_dialog():
    """Display documents in a dialog"""
    st.write("### Kaynak Belgeler")
    for idx, doc in enumerate(st.session_state.data["current_documents"], 1):
        st.write(f"{idx}. {doc}")


@st.dialog("Haberleri indirmek için bir gün seç")
def show_date_picker_dialog():
    # Fetch available dates on first load or when needed
    if not st.session_state.data["available_dates"]:
        with st.spinner("Seçenekler yükleniyor..."):
            available_dates = fetch_available_dates()
            if not available_dates:
                st.info("İndirilebilir haber bulunamadı.")
                return
        st.session_state.data["available_dates"].extend(available_dates)

    dates = st.session_state.data["available_dates"]
    selected_date = st.selectbox(
        "Hangi tarihin haberlerini indirmek istersiniz?",
        options=dates,
        format_func=lambda d: d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)
    )
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Submit", key="submit_btn"):
            on_date_selected(selected_date)
            st.rerun()
    
    with col2:
        if st.button("Cancel", key="cancel_btn"):
            close_date_dialog()
            st.rerun()


@st.dialog("Giriş Yap", width="medium", on_dismiss=close_login_dialog)
def show_login_dialog():
    """Display login dialog"""
    now = time.time()
    authentication = st.session_state.authentication

    if now < authentication["locked_until"]:
        remaining = int(authentication["locked_until"] - now)
        st.error(f"Çok fazla deneme. {remaining}s içinde tekrar deneyin.")
        return

    st.write("### Giriş Yapın")
    pwd = st.text_input("Şifre", type="password", key="login_pwd_input")

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Giriş", key="login_submit_btn", use_container_width=True):
            login_response = send_login_request(pwd)
            if login_response:
                on_authenticated(login_response.get("access_token"))
                close_login_dialog()
                st.rerun()
            else:
                st.error("Yanlış şifre")
                if on_authentication_failed():
                    st.error("Çok fazla başarısız deneme. Geçici olarak kilitlendim.")
    
    with col2:
        if st.button("İptal", key="login_cancel_btn", use_container_width=True):
            close_login_dialog()
            st.rerun()


def render_menu():
    def render_new_conversation_button():
        if st.button("➕ Yeni Konuşma Başlat", key="start_new_conv_btn", use_container_width=True):
            reset_chat()
            st.rerun()

    def render_login_button():
        if st.button("🔐 Giriş Yap", key="login_menu_btn", use_container_width=True):
            open_login_dialog()
    
    def render_logout_button():
        if st.button("🚪 Çıkış Yap", key="logout_btn", use_container_width=True):
            st.session_state.authentication["authenticated"] = False
            st.session_state.authentication["token"] = None
            st.session_state.authentication["attempts"] = 0
            st.session_state.authentication["locked_until"] = 0
            st.rerun()

    def render_conversations():
        st.subheader("📋 Konuşmalar")
    
        with st.container(height=800, border=True):
            conversations = st.session_state.data["conversations"]

            for conv in conversations:
                if st.button(
                    f"📅 {datetime.fromtimestamp(conv['created_at']).strftime(DATE_VISUAL_FORMAT)}\n"
                    f"{conv['first_question'][:40]}...",
                    key=f"conv_{conv['conversation_id']}",
                    use_container_width=True
                ):
                    st.session_state.chat["selected_conversation"] = conv['conversation_id']
                    st.rerun()
            if len(conversations) == 0:
                st.info("Henüz Ulak'a bir soru sormadın.")

    def render_download_options():
        if st.button("📩 Haber bültenleri", key="download_btn", use_container_width=True):
            open_date_dialog()

        if st.session_state.ui["date_dialog_open"]:
            show_date_picker_dialog()

        result = st.session_state.data["download_result"]
        date = st.session_state.data["dialog_selected_date"]

        # Show download button if download_url is available
        if result and result.get("download_url", None) and date:
            st.link_button(
                f"📥 {date.strftime(DATE_VISUAL_FORMAT)} tarihli haberleri indir",
                result["download_url"],
                use_container_width=True
            )
        else:
            set_error_message("İndirme linki oluşturulamadı")
    
    if st.session_state.authentication.get("authenticated", False):
        render_logout_button()
        st.divider()
        render_new_conversation_button()
        st.divider()
        render_conversations()
        st.divider()
        render_download_options()
    else:
        render_login_button()

def render_chat():
    st.title("📰 Ulak'a sor")

    chat = st.session_state.chat

    if is_different_conversation_selected(chat):
        with st.spinner("Konuşma yükleniyor..."):
            chat["messages"] = fetch_messages(chat["selected_conversation"])
            chat["current_conversation_id"] = chat["selected_conversation"]
    
    # Display messages

    if not chat["messages"]:
        st.info("💬 Yeni bir konuşmaya başlamak için Ulak'a soru sor.")

    for msg in chat["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["message"])
            st.caption(f"⏰ {datetime.fromtimestamp(msg['created_at']).strftime(DATE_TIME_VISUAL_FORMAT)}")
            
            # Display documents button if documents exist
            if msg.get("documents") and msg["role"] == "assistant":
                if st.button("📄 Belgeleri Göster", key=f"docs_btn_{id(msg)}", use_container_width=False):
                    st.session_state.data["current_documents"] = msg["documents"]
                    open_document_dialog()

    # Handle message input
    user_input = st.chat_input("Ulak'a soru sor")
    
    # Display documents dialog if open (before early return)
    if st.session_state.ui["document_dialog_open"]:
        show_documents_dialog()
    
    # Display login dialog if open
    if st.session_state.ui["login_dialog_open"]:
        show_login_dialog()
    
    if not user_input:
        return

    # If no conversation is selected, start a new one
    if not chat["current_conversation_id"]:
        with st.spinner("Konuşma başlatılıyor..."):
            chat_response = start_chat(user_input)
            
        if not chat_response:
            set_error_message("Konuşma başlatılamadı")
            return

        chat["current_conversation_id"] = chat_response["conversation_id"]
        chat["selected_conversation"] = chat_response["conversation_id"]
        chat["messages"] = []
        
        # Add the new conversation to the list
        st.session_state.data["conversations"].insert(0, chat_response)
    
    chat["messages"].append({"role": "user", "message": user_input, "created_at": datetime.now().timestamp()})
    
    with st.chat_message("user"):
        st.write(user_input)

        
    # Send the message to the chat endpoint
    with st.spinner("Ulak düşünüyor..."):
        agent_response = send_chat_message(chat["current_conversation_id"], user_input)
    
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
        
        chat["messages"].append(assistant_message)
        st.rerun()


def render_audio_view():
    st.title("🎧 Haberleri dinle")

    languages = {"Deutsch": "german", "Türkçe": "turkish"}
    language_label = st.selectbox("Dil", list(languages))
    language = languages[language_label]
    audio_state = st.session_state.audio

    if audio_state["language"] != language:
        available_dates = fetch_playback_options(language)
        audio_state.update({
            "language": language,
            "available_dates": available_dates or [],
            "options_error": available_dates is None,
            "playback_key": None,
            "playback": None,
        })

    dates = audio_state["available_dates"]
    if not dates:
        if audio_state["options_error"]:
            st.error("Dinleme seçenekleri yüklenemedi. Lütfen bağlantınızı kontrol edip tekrar deneyin.")
            return
        st.info(f"{language_label} için dinlenebilir haber bulunamadı.")
        return

    selected_date = st.selectbox(
        "Haber tarihi",
        options=dates,
        format_func=lambda date: date.strftime(DATE_VISUAL_FORMAT),
        key=f"audio_date_{language}",
    )
    playback_key = (language, selected_date.strftime("%Y-%m-%d"))

    if st.button("Oynatıcıyı aç", type="primary", use_container_width=True):
        with st.spinner("Ses ve metin yükleniyor..."):
            playback = fetch_playback(selected_date, language)
        if playback:
            audio_state["playback_key"] = playback_key
            audio_state["playback"] = playback
        else:
            audio_state["playback_key"] = None
            audio_state["playback"] = None
            st.error("Oynatıcı yüklenemedi. Lütfen daha sonra tekrar deneyin.")

    if (
        audio_state["playback"]
        and audio_state["playback_key"] == playback_key
    ):
        render_audio_player(
            audio_url=audio_state["playback"]["audio_url"],
            segments=audio_state["playback"]["segments"],
            language=language,
            selected_date=playback_key[1],
        )


def main():
    st.set_page_config(page_title="Ulak", layout="wide")

    init_state()

    # Check if authentication is still valid
    authenticated = st.session_state.authentication.get("authenticated", False)
    
    # If not authenticated, open login dialog automatically
    if not authenticated:
        st.info("💬 Lütfen giriş yaparak başlayın.")
        
        error_message = st.session_state.ui.get("error")
        if error_message:
            st.error(error_message)
            st.session_state.ui["error"] = None
        
        # Show login dialog
        show_login_dialog()

    else:
        # Always show the login dialog if it should be open
        if st.session_state.ui.get("login_dialog_open"):
            show_login_dialog()

        with st.sidebar:
            selected_view = st.radio(
                "Uygulama",
                options=["Ulak'a sor", "Haberleri dinle"],
                label_visibility="collapsed",
            )
            render_menu()
    
        if selected_view == "Haberleri dinle":
            render_audio_view()
        else:
            render_chat()

if __name__ == "__main__":
    main()
