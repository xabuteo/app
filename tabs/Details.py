# tabs/detail.py
import streamlit as st

def page(selected_event):
    st.subheader(f"Event: {selected_event['NAME']}")
    st.write(f"Starts on: {selected_event['START_DATE']}")
