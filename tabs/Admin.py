import streamlit as st
from utils import get_snowflake_connection
from admin import event_status, seed_and_group, auto_group, generate_matches

def page(selected_event):
    st.subheader("Event Admin")

    # Extract key info
    event_id = selected_event.get("ID")
    event_status_value = selected_event.get("EVENT_STATUS")
    user_email = selected_event.get("UPDATE_BY", "admin@xabuteo.com")

    # Run sections
    event_status.render(event_id, event_status_value, user_email)
    seed_and_group.render(event_id)
    auto_group.render(event_id, user_email)
    generate_matches.render_match_generation(event_id)
