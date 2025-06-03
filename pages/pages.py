import streamlit as st

TABS = st.tabs(
    tabs=[
        "DETAIL",
        "SCORES",
        "RESULT",
    ]
)

PAGES = [detail, scores, result]

for t, p in zip(TABS, PAGES):
    with t:
        p.page()
