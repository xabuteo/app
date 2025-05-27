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
    import requests
    from urllib.parse import urlencode
    import streamlit as st

    if "access_token" in st.session_state:
        return st.session_state.get("user_info")

    query_params = st.query_params

    # Prevent reusing the same code by checking session
    if "auth_code_used" in st.session_state:
        return None

    if "code" in query_params:
        code = query_params["code"]
        if isinstance(code, list):
            code = code[0]

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
                st.session_state["auth_code_used"] = True
                user_info = get_userinfo(access_token)
                st.session_state["user_info"] = user_info
                st.session_state["user_email"] = user_info.get("email", "")
            
                # ✅ Clear query parameters to prevent invalid_grant on refresh
                #st.query_params.clear()
            
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


# Keys used in session state
SESSION_KEYS = ["user_email", "access_token", "user_info"]

def initialize_session():
    """Initialize expected session keys."""
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("user_info", {})

def is_logged_in():
    """Returns True if user_info is in session and has an email."""
    return (
        "user_info" in st.session_state and
        isinstance(st.session_state.user_info, dict) and
        st.session_state.user_info.get("email")
    )

def check_auth():
    """Ensure user is authenticated; otherwise, try login or stop app."""
    if not is_logged_in():
        user_info = login_callback()
        if user_info:
            st.session_state["user_info"] = user_info
            st.session_state["user_email"] = user_info.get("email", "")
            # access_token should already be set inside login_callback
        else:
            st.warning("🔐 You are not logged in.")
            st.markdown("[Click here to log in](/)")
            st.stop()

def logout():
    """Clear all session keys on logout."""
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)
