import streamlit as st
import requests
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Base URL - modify this to match your API endpoint
API_BASE_URL = "http://localhost:8081"  # Adjust as needed


def fetch_available_dates():
    """Fetch available dates from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/download-options")
        response.raise_for_status()
        dates = response.json()
        # Convert string dates to datetime objects if needed
        return sorted([datetime.strptime(d, "%Y-%m-%d") if isinstance(d, str) else d for d in dates])
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch available dates: {e}")
        st.error("Failed to load available dates")
        return []


def submit_selected_date(selected_date):
    """Send the selected date to the API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/download",
            json={"date_str": selected_date.strftime("%Y-%m-%d")}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to submit date: {e}")
        st.error(f"Failed to process date: {e}")
        return None


@st.dialog("Select a date to download")
def show_date_picker(available_dates):
    """Display date picker dialog with available dates only"""
    if not available_dates:
        st.error("No available dates to select")
        return
    
    # Initialize session state for selected date in dialog
    if "dialog_selected_date" not in st.session_state:
        st.session_state.dialog_selected_date = available_dates[0]
    
    # Create a date input that only accepts available dates
    st.write("Available dates:")
    selected_date = st.selectbox(
        "Pick a date",
        options=available_dates,
        format_func=lambda d: d.strftime("%Y-%m-%d"),
        key="date_selector"
    )
    
    # Store the selected date in session state
    st.session_state.dialog_selected_date = selected_date
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Submit", key="submit_btn"):
            # Send request to API
            result = submit_selected_date(selected_date)
            if result:
                # Store the result in session state
                st.session_state.download_result = result
                st.success(result.get("message", "Successfully submitted!"))
                
                # Show download button if download_url is available
                if result.get("download_url"):
                    st.link_button(
                        "📥 Download File",
                        result.get("download_url"),
                        help="Click to download your audio file"
                    )
                st.session_state.dialog_open = False
                st.rerun()
    
    with col2:
        if st.button("Cancel", key="cancel_btn"):
            st.session_state.dialog_open = False
            st.rerun()


def main():
    """Main application"""
    st.set_page_config(page_title="Daily News Downloader", layout="centered")
    st.title("📰 Daily News Downloader")
    
    # Initialize session state
    if "dialog_open" not in st.session_state:
        st.session_state.dialog_open = False
    
    # Fetch available dates on first load or when needed
    if "available_dates" not in st.session_state:
        with st.spinner("Loading available dates..."):
            st.session_state.available_dates = fetch_available_dates()
    
    available_dates = st.session_state.available_dates
    
    # Display available dates info
    if available_dates:
        st.info(f"Available dates: {available_dates[0].strftime('%Y-%m-%d')} to {available_dates[-1].strftime('%Y-%m-%d')}")
    
    # Display download result if available
    if "download_result" in st.session_state:
        result = st.session_state.download_result
        st.success(result.get("message", "Download link generated!"))
        if result.get("download_url"):
            st.link_button(
                "📥 Download File",
                result.get("download_url"),
                help="Click to download your audio file. Link expires in 3 minutes.",
                use_container_width=True
            )
        # Clear the result after displaying
        del st.session_state.download_result
    
    # Main button to open date picker dialog
    if st.button("📥 Download news", key="download_btn", use_container_width=True):
        st.session_state.dialog_open = True
    
    # Show date picker if dialog is open
    if st.session_state.dialog_open:
        show_date_picker(available_dates)


if __name__ == "__main__":
    main()