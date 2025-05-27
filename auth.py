# auth.py

import streamlit as st
import requests
from urllib.parse import urlencode
import uuid
import base64
import hashlib
import os

# Secrets from Streamlit config
AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
CLIENT_ID = st.secrets["auth0"]["client_id"]
REDIRECT_URI = st.secrets["auth0"]["redirect_uri"]

TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"

# --- Helper Functions ---

def generate_pkce_pair():
    """Generate code_verifier and code_challenge for PKCE."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).rstrip(b'=').decode('utf-8')
    return code_verifier, code_challenge

def get_login_url():
    """Construct the Auth0 login URL with PKCE challenge."""
    code_verifier, code_challenge = generate_pkce_pair()
    st.session_state["code_verifier"] = code_verifier

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": str(uuid.uuid4())
    }
    return f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"

def login_callback():
    """Handle the callback from Auth0 after login."""
    if "access_token" in st.session_state:
        return st.session_state.get("user_info")

    query_params = st.query_params

    if "auth_code_used" in st.session_state:
        return None

    if "code" in query_params:
        code = query_params["code"]
        if isinstance(code, list):
            code = code[0]

        code_verifier = st.session_state.get("code_verifier", "")

        try:
            response = requests.post(
                TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": code_verifier
                }),
            )

            token_data = response.json()
            access_token = token_data.get("access_token")

            if access_token:
                st.session_state["access_token"] = access_token
                st.session_state["auth_code_used"] = True
                user_info = get_userinfo(access_token)
                st.session_state["user_info"] = user_info
                st.session_state["user_email"] = user_info.get("email", "")

                # ✅ Clear query params to avoid reusing the code
                st.query_params.clear()
                return user_info

            else:
                st.error("❌ Failed to get access token.")
                st.write(token_data)

        except Exception as e:
            st.error(f"❌ Token exchange failed: {e}")
    return None

def get_userinfo(access_token):
    """Get user profile info from Auth0."""
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

def logout_button():
    """Display a logout button that redirects to Auth0 logout."""
    domain = AUTH0_DOMAIN
    return_to = REDIRECT_URI
    client_id = CLIENT_ID

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

# --- Session Management Utilities ---

SESSION_KEYS = ["user_email", "access_token", "user_info", "auth_code_used", "code_verifier"]

def initialize_session():
    for key in SESSION_KEYS:
        st.session_state.setdefault(key, None)

def is_logged_in():
    return (
        "user_info" in st.session_state and
        isinstance(st.session_state.user_info, dict) and
        st.session_state.user_info.get("email")
    )

def check_auth():
    if not is_logged_in():
        user_info = login_callback()
        if user_info:
            st.session_state["user_info"] = user_info
            st.session_state["user_email"] = user_info.get("email", "")
        else:
            st.warning("🔐 You are not logged in.")
            st.markdown("[Click here to log in](/)")
            st.stop()

def logout():
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)
