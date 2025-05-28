import streamlit as st

# Page content
st.title("📊 Dashboard")
# Access control
#if "user_info" not in st.session_state:
if st.button(
    "✨ Sign up to the DataFan Store",
    type="primary",
    key="checkout-button",
    use_container_width=True,
):
    st.login("auth0")
#st.success(f"Welcome, {user_name}!")
