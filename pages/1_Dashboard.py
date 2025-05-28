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
    st.success(f"Welcome, {st.user.email}!")
    st.success(f"Welcome, {st.user.given_name}!")
    st.success(f"Welcome, {st.user.family_name}!")
    st.success(f"Welcome, {st.user.sub}!")
    if st.button(
        "✨ Log out",
        type="primary",
        key="checkout-button",
        use_container_width=True,
    ):
        st.logout()
