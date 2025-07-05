import streamlit as st
from sidebar_utils import render_sidebar_widgets

# Page content
st.title("📊 Dashboard")
# Access control
if not st.user.is_logged_in:
    if st.button(
        "✨ Login or Sign up to the Xabuteo site",
        type="primary",
        key="checkout-button",
        use_container_width=True,
    ):
        st.login("auth0")
else:
    st.success(f"Welcome, {st.user.email}!")
    st.success(f"Welcome, {st.user.sub}!")
    st.json(st.user.to_dict())
    if st.button(
        "✨ Log out",
        type="primary",
        key="checkout-button",
        use_container_width=True,
    ):
        st.logout()

if st.session_state.get("test_mode"):
    render_sidebar_widgets()
