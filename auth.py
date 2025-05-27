# auth.py

import streamlit as st
from urllib.parse import urlencode
import requests
import uuid
import os
import base64
import hashlib

# Load secrets
AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
CLIENT_ID = st.secrets["auth0"]["client_id"]
REDIRECT_URI = st.secrets["auth0"]["redirect_uri"]

# Constants
TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"
SESSION_KEYS = ["user_email", "access_token", "user_info", "code_verifier", "auth_code_used"]

# 🔐 Generate PKCE values
def generate_pkce_pair():
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode("utf-8")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode("utf-8")
    return code_verifier, code_challenge

# 🚪 Auth0 logout
def logout_button():
    logout_url = (
        f"https://{AUTH0_DOMAIN}/v2/logout?"
        + urlencode({
            "client_id": CLIENT_ID,
            "returnTo": REDIRECT_URI
        })
    )
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.markdown(
            f'<meta http-equiv="refresh" content="0;URL=\'{logout_url}\'" />',
            unsafe_allow_html=True,
        )

# 🔑 Generate login URL with PKCE
def get_login_url():
    code_verifier, code_challenge = generate_pkce_pair()
    st.session_state["code_verifier"] = code_verifier  # Store for token exchange

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": str(uuid.uuid4()),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    return f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"

# 👤 Handle Auth0 callback
def login_callback():
    if "access_token" in st.session_state:
        return st.session_state.get("user_info")

    query_params = st.query_params

    if "auth_code_used" in st.session_state:
        return None

    if "code" in query_params:
        code = query_params["code"]
        if isinstance(code, list):
            code = code[0]

        code_verifier = st.session_state.get("code_verifier")
        if not code_verifier:
            st.error("Missing PKCE code_verifier for token exchange.")
            return None

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
                st.query_params.clear()  # Prevent refresh issues
                return user_info
            else:
                st.error("❌ Failed to get access token.")
                st.write(token_data)

        except Exception as e:
            st.error(f"❌ Token exchange failed: {e}")
    return None

# 👥 Get user info from Auth0
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

# 🔒 Session initialization
def initialize_session():
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("user_info", {})

# 🔍 Logged in check
def is_logged_in():
    return (
        "user_info" in st.session_state and
        isinstance(st.session_state.user_info, dict) and
        st.session_state.user_info.get("email")
    )

# ✅ Auth enforcement
def check_auth():
    if not is_logged_in():
        user_info = login_callback()
        if user_info:
            st.session_state["user_info"] = user_info
            st.session_state["user_email"] = user_info.get("email", "")
        else:
            st.warning("🔐 You are not logged in.")
            st.markdown(f"[Click here to log in]({get_login_url()})")
            st.stop()

# ❌ Clear session
def logout():
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)
