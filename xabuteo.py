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
    pg = st.navigation(
        [dashboard_page],
        position="hidden",
    )
    # Head to first page of navigation
    pg.run()
    #st.json(st.user)

