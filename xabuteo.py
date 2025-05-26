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
                MERGE INTO xabuteo.public.registrations AS tgt
                USING (
                    SELECT 
                        %s AS email,
                        %s AS first_name,
                        %s AS last_name,
                        %s AS auth_id,
                        CURRENT_TIMESTAMP() AS date_registered,
                        CURRENT_TIMESTAMP() AS updated_at,
                        %s AS updated_by
                ) AS src
                ON tgt.email = src.email
                WHEN NOT MATCHED THEN
                    INSERT (email, first_name, last_name, auth_id, date_registered, updated_at, updated_by)
                    VALUES (src.email, src.first_name, src.last_name, src.auth_id, src.date_registered, src.updated_at, src.updated_by)
                """,
                (
                    st.session_state.user_email,
                    user_info.get("given_name", ""),
                    user_info.get("family_name", ""),
                    user_info.get("sub", ""),  # Auth0's unique user ID
                    user_info.get("email", "")
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
