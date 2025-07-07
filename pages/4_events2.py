import streamlit as st
import pandas as pd

# Simulated data
df = pd.DataFrame({
    "ID": [101, 102, 103],
    "EVENT_TITLE": ["Spring Open", "Winter Cup", "Summer Slam"],
    "EVENT_START_DATE": ["2025-08-01", "2025-07-01", "2025-09-15"]
})

# Display selection
selected_id = st.radio(
    "Select an Event:",
    options=df["ID"],
    format_func=lambda x: f"{df[df['ID'] == x]['EVENT_TITLE'].values[0]} ({df[df['ID'] == x]['EVENT_START_DATE'].values[0]})"
)

# Display full table (non-editable)
st.data_editor(
    df,
    disabled=True,
    hide_index=True,
    use_container_width=True
)

st.success(f"Selected event ID: {selected_id}")
