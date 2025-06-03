# tabs/detail.py
import streamlit as st

def page(event):
    st.subheader(f"Event: {event['NAME']}")
    st.write(f"Starts on: {event['START_DATE']}")
