import streamlit as st
import pandas as pd

# in detail.py
def page(selected_event):
    with st.container(border=True):
        # Header and subheader
        st.subheader(selected_event.get("EVENT_TITLE", "Untitled Event"))
        eventtype = selected_event.get("EVENT_TYPE", "")
        st.markdown(f"**{eventtype}**")
    
        col1, col2 = st.columns(2)
        with col1:
            # Date display logic
            start_date = selected_event.get("EVENT_START_DATE", "")
            end_date = selected_event.get("EVENT_END_DATE", "")
            if start_date == end_date or not end_date:
                date_str = f"**Date:** {start_date}"
            else:
                date_str = f"**Date:** {start_date} to {end_date}"
    
            # Location
            location = selected_event.get("EVENT_LOCATION", "Unknown Location")
    
            # Display main event info
            st.markdown(date_str)
            st.markdown(f"**Location:** {location}")
        with col2:
            # Competitions
            competition = selected_event.get("COMPETITIONS", "Unknown")
    
            # Display main event info
            st.markdown(f"**Competitions:** {competition}")
           
        # Email and comments
        st.markdown(f"**Contact Email:** {selected_event.get('EVENT_EMAIL', 'N/A')}")
        st.markdown(f"**Comments:** {selected_event.get('EVENT_COMMENTS', 'None')}")
