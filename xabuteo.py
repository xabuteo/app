# xabuteo.py

import streamlit as st
from auth import get_login_url, login_callback, logout_button
from utils import get_snowflake_connection, ensure_profile_complete

# Set page configuration
st.set_page_config(
    page_title="Xabuteo",
    page_icon="✨",
    initial_sidebar_state="collapsed",
    layout="centered",
)

# Define app pages
login_page = st.Page("./pages/1_Dashboard.py", title="Dashboard", icon=":material/home:")
profile_page = st.Page("./pages/2_Profile.py", title="Profile", icon=":material/person:")
club_page = st.Page("./pages/3_Clubs.py", title="Clubs", icon=":material/groups:")

# 🔐 Handle Auth0 login callback or silent login
user_info = login_callback()

if user_info:
    st.session_state.user_info = user_info
    st.session_state.user_email = user_info.get("email", "")
    st.success(f"✅ Logged in as {st.session_state.user_email}")

    # 📥 Save to Snowflake if user is new
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
    # 🚪 User not logged in: show login screen
    # st.warning("🔐 You are not logged in.")
    # login_url = get_login_url()
    # st.markdown(f"[Click here to log in]({login_url})", unsafe_allow_html=True)
    # st.stop()
    # 🎉 Main app navigation
    pg = st.navigation(
        [login_page, profile_page, club_page],
        title="Xabuteo",
        title_icon="✨",
    )
    pg.run()

# ✅ Check profile completeness
ensure_profile_complete()

# Optional: Logout button
logout_button()
