# auth.py

import streamlit as st
from urllib.parse import urlencode, urlparse, parse_qs
import requests
import uuid

AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
CLIENT_ID = st.secrets["auth0"]["client_id"]
CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
REDIRECT_URI = st.secrets["auth0"]["redirect_uri"]

TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"

# auth.py snippet

def logout_button():
    domain = st.secrets["auth0"]["domain"]
    client_id = st.secrets["auth0"]["client_id"]
    return_to = st.secrets["auth0"]["redirect_uri"]

    logout_url = (
        f"https://{domain}/v2/logout?"
        + urlencode({
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

def get_login_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": str(uuid.uuid4())
    }
    return f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"
   
def login_callback():
    # 1. Check if access token is already stored
    if "access_token" in st.session_state:
        user_info = get_userinfo(st.session_state["access_token"])
        if user_info:
            return user_info

    # 2. Attempt silent login from URL params
    query_params = st.query_params()

    if "code" in query_params:
        code = query_params["code"][0]
        # 3. Exchange code for access token
        try:
            response = requests.post(
                TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": REDIRECT_URI
                }),
            )
            token_data = response.json()
            access_token = token_data.get("access_token")

            if access_token:
                st.session_state["access_token"] = access_token
                user_info = get_userinfo(access_token)
                return user_info
            else:
                st.error("❌ Failed to get access token.")
                st.write(token_data)

        except Exception as e:
            st.error(f"❌ Auth0 token exchange failed: {e}")

    # 4. No login possible
    return None

def get_userinfo(access_token):
    try:
        response = requests.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error("❌ Failed to fetch user info.")
            st.write(response.text)
            return None
    except Exception as e:
        st.error(f"❌ Error getting user info: {e}")
        return None
