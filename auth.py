# auth.py

import streamlit as st
from urllib.parse import urlencode
import requests
import uuid
import base64
import hashlib
import os

# Load secrets
AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
CLIENT_ID = st.secrets["auth0"]["client_id"]
CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
REDIRECT_URI = st.secrets["auth0"]["redirect_uri"]

TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"

# Session keys
SESSION_KEYS = ["user_email", "access_token", "user_info", "code_verifier", "auth_state"]

def generate_pkce_pair():
    """Generate a code_verifier and code_challenge using SHA256 (S256 method)."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode("utf-8")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("utf-8")).digest()
    ).rstrip(b'=').decode("utf-8")
    return code_verifier, code_challenge

def get_login_url():
    """Create Auth0 login URL with PKCE and state handling."""
    # Only generate once per login attempt
    if "code_verifier" not in st.session_state or "auth_state" not in st.session_state:
        code_verifier, code_challenge = generate_pkce_pair()
        st.session_state["code_verifier"] = code_verifier
        st.session_state["code_challenge"] = code_challenge
        st.session_state["auth_state"] = str(uuid.uuid4())

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": st.session_state["auth_state"],
        "code_challenge": st.session_state["code_challenge"],
        "code_challenge_method": "S256",
    }
    return f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"

def login_callback():
    """Process Auth0 redirect with code and exchange for tokens."""
    if "access_token" in st.session_state:
        return st.session_state.get("user_info")

    query_params = st.query_params

    if "code" in query_params and "state" in query_params:
        returned_state = query_params["state"]
        expected_state = st.session_state.get("auth_state")

        if returned_state != expected_state:
            st.error("❌ State mismatch. Possible CSRF attack.")
            return None

        code = query_params["code"]
        code_verifier = st.session_state.get("code_verifier")

        if not code_verifier:
            st.error("❌ Missing PKCE code_verifier for token exchange.")
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
                    "code_verifier": code_verifier,
                }),
            )

            token_data = response.json()
            access_token = token_data.get("access_token")

            if access_token:
                st.session_state["access_token"] = access_token
                user_info = get_userinfo(access_token)
                st.session_state["user_info"] = user_info
                st.session_state["user_email"] = user_info.get("email", "")

                # Clear query params to prevent refresh issues
                st.query_params.clear()
                return user_info
            else:
                st.error("❌ Failed to get access token.")
                st.json(token_data)

        except Exception as e:
            st.error(f"❌ Token exchange failed: {e}")

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

def check_auth():
    """Ensure user is authenticated; otherwise, try login or stop app."""
    if not is_logged_in():
        user_info = login_callback()
        if user_info:
            st.session_state["user_info"] = user_info
            st.session_state["user_email"] = user_info.get("email", "")
        else:
            st.warning("🔐 You are not logged in.")
            st.markdown(f"[Click here to log in]({get_login_url()})")
            st.stop()

def is_logged_in():
    """Returns True if user_info is in session and has an email."""
    return (
        "user_info" in st.session_state and
        isinstance(st.session_state.user_info, dict) and
        st.session_state.user_info.get("email")
    )

def logout_button():
    """Add logout button to the UI."""
    logout_url = (
        f"https://{AUTH0_DOMAIN}/v2/logout?"
        + urlencode({
            "client_id": CLIENT_ID,
            "returnTo": REDIRECT_URI
        })
    )

    if st.button("🚪 Logout"):
        for key in SESSION_KEYS:
            st.session_state.pop(key, None)
        st.markdown(
            f'<meta http-equiv="refresh" content="0;URL=\'{logout_url}\'" />',
            unsafe_allow_html=True,
        )

def logout():
    """Clear all session keys on logout."""
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)
