import streamlit as st
from auth import initialize_session, check_auth

#initialize_session()
#check_auth()
#st.set_page_config(page_title="Dashboard")
   
# Extract user info
user_info = st.session_state["user_info"]
user_email = user_info.get("email", "Unknown")
user_name = user_info.get("name") or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip() or user_email

# Page content
st.title("📊 Dashboard")
# Access control
if "user_info" not in st.session_state:
   if st.button(
       "✨ Sign up to the Xabuteo site",
       type="primary",
       key="checkout-button",
       use_container_width=True,
   ):
   st.login("auth0")
st.success(f"Welcome, {user_name}!")
