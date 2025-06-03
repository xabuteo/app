# tabs/detail.py
import streamlit as st

def page(selected_event):
    st.subheader(f"Event: {selected_event['EVENT_TITLE']}")
    st.write(f"Starts on: {selected_event['EVENT_START_DATE']}")
