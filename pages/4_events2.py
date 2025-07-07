import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from tabs import Details, Register, Tables, Scores, Result, Admin
from admin import new_event

st.set_page_config(page_title="Events", layout="wide")
st.title("📅 Events")

# Load events
try:
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events_v ORDER BY EVENT_START_DATE DESC")
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(rows, columns=cols)
except Exception as e:
    st.error(f"Error loading events: {e}")
    df = pd.DataFrame()
finally:
    cursor.close()
    conn.close()

# Handle no data
if df.empty:
    st.info("No events found.")
    new_event.add_new_event()

else:
    if "selected_event_id" not in st.session_state:
        st.session_state.selected_event_id = None

    selected_event_id = st.session_state.selected_event_id

    if not selected_event_id:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            title_filter = st.text_input("Search by Title")
        with col2:
            type_filter = st.selectbox("Event Type", ["All"] + sorted(df["EVENT_TYPE"].dropna().unique()))
        with col3:
            status_filter = st.selectbox("Event Status", ["All"] + sorted(df["EVENT_STATUS"].dropna().unique()))

        df_filtered = df.copy()

        if title_filter:
            df_filtered = df_filtered[df_filtered["EVENT_TITLE"].str.contains(title_filter, case=False, na=False)]
        if type_filter != "All":
            df_filtered = df_filtered[df_filtered["EVENT_TYPE"] == type_filter]
        if status_filter != "All":
            df_filtered = df_filtered[df_filtered["EVENT_STATUS"] == status_filter]

        if df_filtered.empty:
            st.info("No events match the filters.")
        else:
            display_cols = [
                "ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_START_DATE", "EVENT_END_DATE",
                "EVENT_LOCATION", "EVENT_STATUS"
            ]
            df_display = df_filtered[display_cols].copy()
            df_display["EVENT_START_DATE"] = pd.to_datetime(df_display["EVENT_START_DATE"]).dt.strftime('%Y-%m-%d')
            df_display["EVENT_END_DATE"] = pd.to_datetime(df_display["EVENT_END_DATE"]).dt.strftime('%Y-%m-%d')

            selection = st.dataframe(
                df_display,
                selection_mode="single-row",
                on_select="rerun",
                hide_index=True,
                use_container_width=True,
                key="event_table"
            )
            
            if selection and selection.get("rows"):
                row_index = selection["rows"][0]  # Row index in df
                selected_id = df.iloc[row_index]["ID"]
                st.session_state["selected_event_id"] = selected_id
            
            selection.selection
            st.write("Selected Event:", st.session_state.get("selected_event_id", False))

            new_event.add_new_event()

    else:
        # Back button
        st.button("🔙 Back to Event List", on_click=lambda: st.session_state.pop("selected_event_id"))

        selected_event = df[df["ID"] == selected_event_id].iloc[0].to_dict()
        TABS = st.tabs(["DETAILS", "REGISTER", "TABLES", "SCORES", "RESULT", "ADMIN"])
        PAGES = [Details, Register, Tables, Scores, Result, Admin]
        for tab, page_module in zip(TABS, PAGES):
            with tab:
                page_module.page(selected_event)

# Optional test mode
if st.session_state.get("test_mode"):
    from sidebar_utils import render_sidebar_widgets
    render_sidebar_widgets()
