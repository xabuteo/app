import streamlit as st

st.set_page_config(page_title="Logout")

st.title("🚪 Logout")

if st.button("Log out"):
    st.session_state.clear()
    st.success("🔒 You have been logged out.")
    st.rerun()
