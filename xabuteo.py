# xabuteo.py

import streamlit as st
from auth import get_login_url, login_callback, logout_button
from utils import get_snowflake_connection

st.set_page_config(page_title="Xabuteo", layout="centered")
st.title("🏓 Xabuteo – Login")

# 1️⃣ If not yet in session_state, attempt Auth0 callback
if "user_info" not in st.session_state:
    user_info = login_callback()
    if user_info:
        # Successful login: store user_info and user_email
        st.session_state.user_info = user_info
        st.session_state.user_email = user_info.get("email", "")
        st.success(f"✅ Logged in as {st.session_state.user_email}")

        # Insert into Snowflake (if new)
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                MERGE INTO xabuteo.public.registrations tgt
                USING (SELECT %s AS email, %s AS first_name, %s AS last_name) src
                ON tgt.email = src.email
                WHEN NOT MATCHED THEN INSERT (email, first_name, last_name)
                VALUES (src.email, src.first_name, src.last_name)
                """,
                (
                    st.session_state.user_email,
                    user_info.get("given_name", ""),
                    user_info.get("family_name", ""),
                ),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    else:
        # Not yet logged in: show login link and stop
        st.markdown("🔐 You are not logged in.")
        st.markdown(f"[Click here to log in]({get_login_url()})")
        st.stop()

# 2️⃣ Authenticated area
st.success(f"Welcome, {st.session_state.user_email}!")
st.markdown("You can now use the app’s features.")

# 3️⃣ Show Logout button (via Auth0)
logout_button()
