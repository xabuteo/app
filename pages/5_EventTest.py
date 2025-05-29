import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection

def show():
    st.title("📅 Events")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xabuteo.public.events_v ORDER BY EVENT_START_DATE DESC")
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"Error loading events: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.info("No events found.")
        return

    # Optional filters (title, type, status)
    st.subheader("🔍 Search and Filter")
    col1, col2, col3 = st.columns(3)
    with col1:
        title_filter = st.text_input("Search by Title")
    with col2:
        type_filter = st.selectbox("Event Type", ["All"] + sorted(df["EVENT_TYPE"].dropna().unique()))
    with col3:
        status_filter = st.selectbox("Event Status", ["All"] + sorted(df["EVENT_STATUS"].dropna().unique()))

    # Apply filters
    if title_filter:
        df = df[df["EVENT_TITLE"].str.contains(title_filter, case=False, na=False)]
    if type_filter != "All":
        df = df[df["EVENT_TYPE"] == type_filter]
    if status_filter != "All":
        df = df[df["EVENT_STATUS"] == status_filter]

    # Select display columns
    display_cols = [
        "ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_START_DATE", "EVENT_END_DATE",
        "EVENT_LOCATION", "EVENT_STATUS"
    ]
    df_display = df[display_cols]

    st.markdown("### 📋 Event List (Click a row to register)")

    # Configure ag-Grid
    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_pagination()
    grid_options = gb.build()

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        enable_enterprise_modules=False,
        height=400,
        theme="streamlit"
    )

    selected = grid_response["selected_rows"]

    if selected:
        selected_event = selected[0]
        event_title = selected_event["EVENT_TITLE"]
        if st.button(f"📝 Register for '{event_title}'"):
            st.success(f"✅ You're registered for **{event_title}**! (stub functionality)")

show()
