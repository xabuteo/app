import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection

st.set_page_config(page_title="Events", layout="wide")

def show():
    st.title("📅 Events")

    # Load events
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

    # Filters
    st.subheader("🔍 Search and Filter")
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

    st.markdown("### 📋 Event List (Click a row to view details)")

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
    max_rows_to_show = 10
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

    selected = grid_response["selected_rows"]
    if isinstance(selected, pd.DataFrame):
        selected = selected.to_dict(orient="records")
        
    # ✅ Make sure selected is a list and not empty
    if selected and isinstance(selected, list) and len(selected) > 0:
        selected_event = selected[0]
        st.subheader(f"📄 Event Details: {selected_event.get('EVENT_TITLE', '')}")
    
        # Format boolean as ✅/❌
        def check(val): return "✅" if val else "❌"
    
        # Build a markdown table
        event_details_table = f"""
| **Field**         | **Value**                                | **Field**         | **Value**                                |
|-------------------|-------------------------------------------|-------------------|-------------------------------------------|
| Start Date        | {selected_event.get('EVENT_START_DATE', '')} | End Date          | {selected_event.get('EVENT_END_DATE', '')} |
| Open              | {check(selected_event.get('EVENT_OPEN'))}     | Women             | {check(selected_event.get('EVENT_WOMEN'))}  |
| Junior            | {check(selected_event.get('EVENT_JUNIOR'))}   | Veteran           | {check(selected_event.get('EVENT_VETERAN'))} |
| Teams             | {check(selected_event.get('EVENT_TEAMS'))}    | Status            | {selected_event.get('EVENT_STATUS', '')} |
| Event Type        | {selected_event.get('EVENT_TYPE', '')}        | Location          | {selected_event.get('EVENT_LOCATION', '')} |
| Contact Email     | {selected_event.get('EVENT_EMAIL', '')}       | Comments          | {selected_event.get('EVENT_COMMENTS', '')} |
| Reg Open Date     | {selected_event.get('REG_OPEN_DATE', '')}     | Reg Close Date    | {selected_event.get('REG_CLOSE_DATE', '')} |
    """
    
        st.markdown(event_details_table)
    
        # Action buttons
        st.markdown("### 🛠️ Actions")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.button("✅ Approve", key="approve_btn")
        with col_b:
            st.button("📝 Register", key="register_btn")
        with col_c:
            st.button("❌ Close", key="close_btn")
        with col_d:
            st.button("✔️ Complete", key="complete_btn")

show()
