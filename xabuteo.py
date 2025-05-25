# xabuteo.py

import streamlit as st
from auth import get_login_url, login_callback
from utils import get_snowflake_connection

st.set_page_config(page_title="Xabuteo", layout="centered")
st.title("🏓 Xabuteo – Login")

# Check login state
if "user_info" not in st.session_state:
    user_info = login_callback()
    if user_info:
        st.session_state.user_info = user_info
        st.success(f"✅ Logged in as {user_info['email']}")
        # Insert to your DB here
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                MERGE INTO xabuteo.public.registrations tgt
                USING (SELECT %s AS email, %s AS first_name, %s AS last_name) src
                ON tgt.email = src.email
                WHEN NOT MATCHED THEN INSERT (email, first_name, last_name)
                VALUES (src.email, src.first_name, src.last_name)
            """, (
                user_info["email"],
                user_info.get("given_name", ""),
                user_info.get("family_name", "")
            ))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    else:
        st.markdown("🔐 You are not logged in.")
        st.markdown(f"[Click here to log in]({get_login_url()})")
        st.stop()

# Authenticated area
st.success(f"Welcome, {st.session_state.user_info['email']}")
st.markdown("You can now use the app.")
from auth import logout_button

if "user_email" in st.session_state:
    st.success(f"Logged in as {st.session_state['user_email']}")
    logout_button()
