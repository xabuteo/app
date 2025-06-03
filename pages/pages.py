import streamlit as st

TABS = st.tabs(
    tabs=[
        "PROFILE",
        "CLUBS",
        "EVENTS",
    ]
)

PAGES = [profiles, clubs, events]

for t, p in zip(TABS, PAGES):
    with t:
        p.page()
