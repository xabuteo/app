# auth.py

import streamlit as st
import requests
import uuid
import base64
import hashlib
from urllib.parse import urlencode

AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
CLIENT_ID = st.secrets["auth0"]["client_id"]
CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
REDIRECT_URI = st.secrets["auth0"]["redirect_uri"]

TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"

def generate_pkce_pair():
    """Generate code_verifier and code_challenge for PKCE."""
    code_verifier = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')
    code_verifier = code_verifier[:43]  # Max length 128, min 43
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

def get_login_url():
    """Create Auth0 login URL with PKCE parameters."""
    code_verifier, code_challenge = generate_pkce_pair()
    st.session_state["code_verifier"] = code_verifier
    state = str(uuid.uuid4())
    st.session_state["auth_state"] = state

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"

def login_callback():
    query_params = st.query_params
    if "code" not in query_params:
        return None

    code = query_params["code"]
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    res = requests.post(token_url, json=payload)
    res.raise_for_status()
    tokens = res.json()

    # Fetch user info
    userinfo_res = requests.get(
        f"https://{AUTH0_DOMAIN}/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    userinfo_res.raise_for_status()
    return userinfo_res.json()
    
def login_callbackX():
    """Process Auth0 redirect with authorization code and exchange for token."""
    if "access_token" in st.session_state:
        return st.session_state.get("user_info")

    query_params = st.query_params

    # Prevent reusing the same code
    if "auth_code_used" in st.session_state:
        return None

    if "code" in query_params and "state" in query_params:
        code = query_params["code"]
        state = query_params["state"]

        # Verify state
        if state != st.session_state.get("auth_state"):
            st.error("❌ State mismatch. Possible CSRF attack.")
            return None

        code_verifier = st.session_state.get("code_verifier")
        if not code_verifier:
            st.error("❌ Missing PKCE code_verifier in session.")
            return None

        try:
            # Token exchange
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

                # ✅ Clear query params to avoid repeated logins
                st.query_params.clear()
                return user_info
            else:
                st.error("❌ Failed to get access token.")
                st.write(token_data)

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

def logout_button():
    logout_url = (
        f"https://{AUTH0_DOMAIN}/v2/logout?" +
        urlencode({
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

def is_logged_in():
    return (
        "user_info" in st.session_state and
        isinstance(st.session_state["user_info"], dict) and
        st.session_state["user_info"].get("email")
    )

def check_auth():
    """Ensure user is authenticated."""
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
    for key in ["access_token", "user_info", "user_email", "auth_state", "code_verifier"]:
        st.session_state.pop(key, None)
