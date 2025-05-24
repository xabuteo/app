# auth.py - Auth0 + Streamlit integration

import streamlit as st
import requests
from urllib.parse import urlencode, urlparse, parse_qs

AUTH0_CLIENT_ID = st.secrets["auth0"]["client_id"]
AUTH0_CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
REDIRECT_URI = f"https://{st.runtime.scriptrunner.script_run_context.get_script_run_ctx().runtime.scriptrunner.script_run_context.app_url}"

def build_auth_url():
    query = urlencode({
        "client_id": AUTH0_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
    })
    return f"https://{AUTH0_DOMAIN}/authorize?{query}"

def get_token(code):
    url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    return res.json()

def get_user_info(token):
    res = requests.get(
        f"https://{AUTH0_DOMAIN}/userinfo",
        headers={"Authorization": f"Bearer {token}"}
    )
    res.raise_for_status()
    return res.json()

def login():
    query_params = st.experimental_get_query_params()
    code = query_params.get("code", [None])[0]

    if code:
        token_data = get_token(code)
        user = get_user_info(token_data["access_token"])

        st.session_state["user_email"] = user["email"]
        st.session_state["user_name"] = user.get("name") or user["email"].split("@")[0]

        return user
    else:
        st.markdown(f"[Login with Auth0]({build_auth_url()})")
        return None

def logout_button():
    logout_url = f"https://{AUTH0_DOMAIN}/v2/logout?client_id={AUTH0_CLIENT_ID}&returnTo={REDIRECT_URI}"
    if st.button("Logout"):
        st.session_state.clear()
        st.experimental_set_query_params()
        st.markdown(f"[Click here to logout]({logout_url})")
