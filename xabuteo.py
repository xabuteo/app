import streamlit as st

st.set_page_config(page_title="Xabuteo", layout="wide", initial_sidebar_state="expanded")

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("## 📋 Xabuteo Menu")
    selection = st.radio("Navigate to", list(pages.keys()), label_visibility="collapsed")
