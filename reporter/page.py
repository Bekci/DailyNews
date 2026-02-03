import streamlit as st
from client_wrapper import (
    fetch_available_dates,
    fetch_conversations,
    submit_selected_date,
    fetch_messages,
    start_chat,
    send_chat_message
)
from datetime import datetime

DATE_VISUAL_FORMAT = "%d %b %Y"
DATE_TIME_VISUAL_FORMAT = "%d %b %Y %H:%M"

def init_state():
    if "ui" not in st.session_state:
        st.session_state.ui = {
            "document_dialog_open": False,
            "date_dialog_open": False,
            "error": None
        }

    if "data" not in st.session_state:
        st.session_state.data = {
            "conversations": fetch_conversations(),
            "available_dates": [],
            "dialog_selected_date": None,
            "download_result": None,
            "current_documents": []
        }

    if "chat" not in st.session_state:
        reset_chat()

def reset_chat():
    st.session_state.chat = {
        "current_conversation_id": None,
        "selected_conversation": None,
        "messages": [],
    }        
    

def close_document_dialog():
    st.session_state.ui["document_dialog_open"] = False

def open_document_dialog():
    st.session_state.ui["document_dialog_open"] = True

def close_date_dialog():
    st.session_state.ui["date_dialog_open"] = False

def open_date_dialog():
    st.session_state.ui["date_dialog_open"] = True

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


def render_menu():
    def render_new_conversation_button():
        if st.button("➕ Yeni Konuşma Başlat", key="start_new_conv_btn", use_container_width=True):
            reset_chat()
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
    
    render_new_conversation_button()
    st.divider()
    render_conversations()
    st.divider()
    render_download_options()

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

def main():
    st.set_page_config(page_title="Ulak", layout="wide")

    init_state()

    with st.sidebar:
        render_menu()
    
    render_chat()

if __name__ == "__main__":
    main()
