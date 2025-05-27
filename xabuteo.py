# xabuteo.py

import streamlit as st
from auth import get_login_url, login_callback, logout_button
from utils import get_snowflake_connection, ensure_profile_complete

st.set_page_config(page_title="Xabuteo", layout="centered")
st.title("🏓 Xabuteo – Login")
st.sidebar.write("Session state:", dict(st.session_state))

# 1️⃣ Handle authentication callback and silent login
user_info = login_callback()

if user_info:
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
                INSERT (email, first_name, last_name, auth0_id, date_registered, updated_at, updated_by)
                VALUES (src.email, src.first_name, src.last_name, src.auth_id, src.date_registered, src.updated_at, src.updated_by)
            """,
            (
                st.session_state.user_email,
                user_info.get("given_name", ""),
                user_info.get("family_name", ""),
                user_info.get("sub", ""),
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

# 2️⃣ Ensure user profile is complete
ensure_profile_complete()

# 3️⃣ Authenticated and complete profile area
st.success(f"Welcome, {st.session_state.user_email}!")
st.markdown("You can now use the app’s features.")
query_params = st.query_params

# Write them to the sidebar
st.sidebar.header("Query Parameters")
for key, value in query_params.items():
    st.sidebar.write(f"**{key}**: {value}")
