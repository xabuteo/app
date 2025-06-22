import streamlit as st
import pandas as pd
from utils import get_snowflake_connection  # your custom Snowflake connection helper
from streamlit_extras.switch_page_button import switch_page  # optional: for page switching

def get_data():
    conn = get_snowflake_connection()
    query = "SELECT ID, EVENT_NAME, EVENT_START_DATE FROM EVENTS ORDER BY EVENT_START_DATE DESC"
    df = pd.read_sql(query, conn)
    return df

def main():
    st.title("Event List")

    df = get_data()

    st.dataframe(df, use_container_width=True)

    selected_index = st.radio("Select an event:", df.index, format_func=lambda i: f"{df.loc[i, 'EVENT_NAME']} ({df.loc[i, 'EVENT_START_DATE']})")

    if st.button("Go to Event Page"):
        selected_row = df.loc[selected_index]
        event_id = selected_row['ID']

        # Option 1: Pass event_id via query params (for native Streamlit navigation)
        st.experimental_set_query_params(event_id=event_id)

        # Option 2: Use `streamlit-extras` switch_page
        switch_page("event_detail")  # Assumes you have event_detail.py in pages/

if __name__ == "__main__":
    main()
