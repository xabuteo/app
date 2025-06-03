import streamlit as st
from tabs import Details, Scores, Result

TABS = st.tabs(["DETAILS", "SCORES", "RESULT"])
PAGES = [Details, Scores, Result]

for tab, page_module in zip(TABS, PAGES):
    with tab:
        page_module.page()
