import streamlit as st

TABS = st.tabs(
    tabs=[
        "PROFILE",
        "CLUBS",
        "EVENTS",
    ]
)

PAGES = [2_profiles, 3_clubs, 4_events]

for t, p in zip(TABS, PAGES):
    with t:
        p.page()
