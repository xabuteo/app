import streamlit as st
from tabs import detail, scores, result

TABS = st.tabs(["DETAIL", "SCORES", "RESULT"])
PAGES = [detail, scores, result]

for tab, page_module in zip(TABS, PAGES):
    with tab:
        page_module.page()
