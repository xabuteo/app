import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from streamlit_extras.switch_page_button import switch_page  # optional

def get_data():
    conn = get_snowflake_connection()
    query = "SELECT ID, EVENT_TITLE, EVENT_START_DATE FROM EVENTS ORDER BY EVENT_START_DATE DESC"
    df = pd.read_sql(query, conn)
    return df

def main():
    st.title("📋 Event List")

    df = get_data()

    # Display table header manually
    st.markdown("### Events")
    st.write("| Name | Event Date | Action |")
    st.write("|------|------------|--------|")

    # Display each row with a button
    for idx, row in df.iterrows():
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(row["EVENT_TITLE"])
        with col2:
            st.write(row["EVENT_START_DATE"])
        with col3:
            if st.button("➡️ View", key=f"view_{row['ID']}"):
                # Option 1: Set query params and reload
                st.query_params(event_id=row['ID'])
                # Option 2: Switch to detail page (if using multipage setup)
                switch_page("event_detail")  # assumes pages/event_detail.py

if __name__ == "__main__":
    main()
