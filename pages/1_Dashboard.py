import streamlit as st

st.set_page_config(page_title="Dashboard")

if "user_email" not in st.session_state:
    st.warning("🔐 Please log in first.")
    st.stop()

st.title("📊 Dashboard")
st.success(f"Welcome, {st.session_state['user_name']}!")
