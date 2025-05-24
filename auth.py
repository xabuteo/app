# auth.py

import streamlit as st
from urllib.parse import urlencode
import requests
import uuid

AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
CLIENT_ID = st.secrets["auth0"]["client_id"]
CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
REDIRECT_URI = st.secrets["auth0"]["redirect_uri"]

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
