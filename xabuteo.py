import streamlit as st
from auth import login

st.set_page_config(page_title="Xabuteo with Auth0", layout="centered")

user_info = login()

if user_info:
    st.success(f"Welcome, {user_info.get('name', 'User')}!")
    st.write("Here is your profile info:")
    st.json(user_info)
else:
    st.info("Please sign in to continue.")
