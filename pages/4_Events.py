import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection
from tabs import Details, Register, Tables, Scores, Result, Admin

st.set_page_config(page_title="Events", layout="wide")

def show():
    st.title("📅 Events")
    selected_event_id = st.session_state.get("selected_event_id", None)

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
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.info("No events found.")
        return

    if not selected_event_id:
        col1, col2, col3 = st.columns(3)
        with col1:
            title_filter = st.text_input("Search by Title")
        with col2:
            type_filter = st.selectbox("Event Type", ["All"] + sorted(df["EVENT_TYPE"].dropna().unique()))
        with col3:
            status_filter = st.selectbox("Event Status", ["All"] + sorted(df["EVENT_STATUS"].dropna().unique()))
        if title_filter:
            df = df[df["EVENT_TITLE"].str.contains(title_filter, case=False, na=False)]
        if type_filter != "All":
            df = df[df["EVENT_TYPE"] == type_filter]
        if status_filter != "All":
            df = df[df["EVENT_STATUS"] == status_filter]
    else:
        st.button("🔙 Back to Event List", on_click=lambda: st.session_state.pop("selected_event_id"))

    display_cols = [
        "ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_START_DATE", "EVENT_END_DATE",
        "EVENT_LOCATION", "EVENT_STATUS"
    ]
    df_display = df[display_cols].copy()
    df_display["EVENT_START_DATE"] = pd.to_datetime(df_display["EVENT_START_DATE"]).dt.strftime('%Y-%m-%d')
    df_display["EVENT_END_DATE"] = pd.to_datetime(df_display["EVENT_END_DATE"]).dt.strftime('%Y-%m-%d')

    # Check current selection
    selected_event_id = st.session_state.get("selected_event_id")

    # If selected, filter down
    if selected_event_id:
        df_display = df_display[df_display["ID"] == selected_event_id]

    # Grid config
    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    
    if selected_event_id:
        gb.configure_pagination(enabled=False)
        gb.configure_default_column(filter=False)
    else:
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_default_column(filter=True)

    gb.configure_column("ID", width=70)
    gb.configure_column("EVENT_TITLE", minWidth=200, maxWidth=300)
    gb.configure_column("EVENT_TYPE", width=150)
    gb.configure_column("EVENT_START_DATE", width=120)
    gb.configure_column("EVENT_END_DATE", width=120)
    gb.configure_column("EVENT_STATUS", width=130)

    grid_options = gb.build()

    # Height
    row_height = 42
    header_height = 51
    footer_height = 48
    row_count = len(df_display)
    grid_height = min(row_count, 6) * row_height + header_height + footer_height if not selected_event_id else row_height + header_height

    # Display grid
    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        height=grid_height,
        theme="alpine"
    )

    # Handle new selection
    selected_rows = grid_response["selected_rows"]
    
    # Convert to list of dicts if needed
    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict(orient="records")
    
    if isinstance(selected_rows, list) and len(selected_rows) > 0:
        new_selection = selected_rows[0].get("ID")
        if new_selection != selected_event_id:
            st.session_state["selected_event_id"] = new_selection
            st.rerun()

    # Render tabs if selected
    if selected_event_id:
        selected_event = df[df["ID"] == selected_event_id].iloc[0].to_dict()
        TABS = st.tabs(["DETAILS", "REGISTER", "TABLES", "SCORES", "RESULT", "ADMIN"])
        PAGES = [Details, Register, Tables, Scores, Result, Admin]
        for tab, page_module in zip(TABS, PAGES):
            with tab:
                page_module.page(selected_event)

show()
