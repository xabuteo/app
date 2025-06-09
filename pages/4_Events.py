import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection
from tabs import Details, Register, Tables, Scores, Result, Admin

st.set_page_config(page_title="Events", layout="wide")

def show():
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
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.info("No events found.")
        return

    # Filters
    #st.subheader("🔍 Search and Filter")
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

    display_cols = [
        "ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_START_DATE", "EVENT_END_DATE",
        "EVENT_LOCATION", "EVENT_STATUS"
    ]
    df_display = df[display_cols].copy()

    # Format date columns
    df_display["EVENT_START_DATE"] = pd.to_datetime(df_display["EVENT_START_DATE"]).dt.strftime('%Y-%m-%d')
    df_display["EVENT_END_DATE"] = pd.to_datetime(df_display["EVENT_END_DATE"]).dt.strftime('%Y-%m-%d')

    #st.markdown("### 📋 Event List (Click a row to view details)")

    # AgGrid config
    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_pagination(paginationAutoPageSize=False)
    gb.configure_pagination(paginationPageSize=0)

    gb.configure_column("ID", width=70)
    gb.configure_column("EVENT_TITLE", minWidth=200, maxWidth=300)
    gb.configure_column("EVENT_TYPE", width=150)
    gb.configure_column("EVENT_START_DATE", width=120)
    gb.configure_column("EVENT_END_DATE", width=120)
    gb.configure_column("EVENT_STATUS", width=130)

    grid_options = gb.build()

    row_count = len(df_display)
    max_rows_to_show = 6
    row_height = 48
    header_height = 113
    grid_height = min(row_count, max_rows_to_show) * row_height + header_height

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        enable_enterprise_modules=False,
        height=grid_height,
        theme="material"
    )
    selected_rows = grid_response["selected_rows"]

    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict(orient="records")
    
    if selected_rows and isinstance(selected_rows, list) and len(selected_rows) > 0:
        selected_id = selected_rows[0].get("ID")
        selected_event = df[df["ID"] == selected_id].iloc[0].to_dict()
        TABS = st.tabs(["DETAILS", "REGISTER", "TABLES", "SCORES", "RESULT", "ADMIN"])
        PAGES = [Details, Register, Tables, Scores, Result, Admin]
        
        for tab, page_module in zip(TABS, PAGES):
            with tab:
                page_module.page(selected_event)      
show()
