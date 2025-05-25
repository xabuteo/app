# auth.py snippet

import streamlit as st
import urllib.parse

def logout_button():
    domain = st.secrets["auth0"]["domain"]
    client_id = st.secrets["auth0"]["client_id"]
    return_to = st.secrets["auth0"]["redirect_uri"]

    logout_url = (
        f"https://{domain}/v2/logout?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "returnTo": return_to
        })
    )

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.markdown(
            f'<meta http-equiv="refresh" content="0;URL=\'{logout_url}\'" />',
            unsafe_allow_html=True,
        )
