# xabuteo.py

import streamlit as st
from utils import get_snowflake_connection, ensure_profile_complete

st.set_page_config(
    page_title="Xabuteo",
    page_icon="✨",
    #initial_sidebar_state="collapsed",
    layout="centered",
)

dashboard_page = st.Page("./pages/1_Dashboard.py", title="Dashboard", icon=":material/home:")
profile_page = st.Page("./pages/2_Profile.py", title="Profile", icon=":material/play_arrow:")
club_page = st.Page("./pages/3_Clubs.py", title="Clubs", icon=":material/admin_panel_settings:")

if not st.user.is_logged_in:
    # Not yet logged in: show login link and stop
    pg = st.navigation(
        [dashboard_page],
        position="hidden",
    )
    # Head to first page of navigation
    pg.run()
else:
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
                st.user.email,
                st.user.given_name,
                st.user.family_name,
                st.user.sub,
                st.user.email
            ),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()    
    pg = st.navigation(
        [dashboard_page],
        position="hidden",
    )
    # Head to first page of navigation
    pg.run()
    #st.json(st.user)

