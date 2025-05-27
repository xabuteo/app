import streamlit as st
from auth import initialize_session, check_auth

initialize_session()
check_auth()

st.set_page_config(page_title="Dashboard")

# Access control
if "user_info" not in st.session_state:
    st.warning("🔐 Please log in to access the dashboard.")
    st.stop()

# Extract user info
user_info = st.session_state["user_info"]
user_email = user_info.get("email", "Unknown")
user_name = user_info.get("name") or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip() or user_email

# Page content
st.title("📊 Dashboard")
st.success(f"Welcome, {user_name}!")
st.write("Session state:", dict(st.session_state))
st.write("Session user:", st.json(st.user))
