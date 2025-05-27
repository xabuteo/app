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
    # 1. Check if access token is already stored in session state
    if "access_token" in st.session_state:
        user_info = get_userinfo(st.session_state["access_token"])
        if user_info:
            return user_info

    # 2. Get query params (code, state, etc.)
    query_params = st.query_params

    if "code" in query_params:
        code = query_params.get("code", [None])[0]

        if not code:
            st.error("No authorization code found in URL.")
            return None

        try:
            # 3. Exchange authorization code for access token
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

            if "error" in token_data:
                st.write("Redirect URI used:", REDIRECT_URI)
                st.error(f"Auth0 error: {token_data.get('error_description', token_data['error'])}")
                st.write(token_data)
                return None

            access_token = token_data.get("access_token")
            if access_token:
                st.session_state["access_token"] = access_token

                # Clear query params so code is not reused on refresh
                st.experimental_set_query_params()

                user_info = get_userinfo(access_token)
                return user_info
            else:
                st.write("Redirect URI used:", REDIRECT_URI)
                st.error("❌ Failed to get access token.")
                st.write(token_data)
                return None

        except Exception as e:
            st.error(f"❌ Auth0 token exchange failed: {e}")
            return None

    # 4. No login possible (no code, no token)
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
