import streamlit as st

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
    st.success(f"Welcome, {user_name}!")
