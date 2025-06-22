import streamlit as st

params = st.experimental_get_query_params()
event_id = params.get("event_id", [None])[0]

if event_id:
    st.title(f"Event Details for ID: {event_id}")
    # fetch and show more data from Snowflake based on event_id
else:
    st.warning("No event selected.")
