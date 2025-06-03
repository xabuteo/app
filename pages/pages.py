import streamlit as st
from tabs import details, scores, result

TABS = st.tabs(["DETAILS", "SCORES", "RESULT"])
PAGES = [details, scores, result]

for tab, page_module in zip(TABS, PAGES):
    with tab:
        page_module.page()
