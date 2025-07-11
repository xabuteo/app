import streamlit as st
import pandas as pd
from utils import get_db_connection
from tabs import Details, Register, Tables, Scores, Result, Admin
from admin import new_event
from utils import get_admin_club_ids

st.set_page_config(page_title="Events", layout="wide")
st.title("📅 Events")

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT *, 
        CONCAT(
                    CASE WHEN event_open    THEN 'Open, '    ELSE '' END,
                    CASE WHEN event_women   THEN 'Women, '   ELSE '' END,
                    CASE WHEN event_junior  THEN 'Junior, '  ELSE '' END,
                    CASE WHEN event_veteran THEN 'Veteran, ' ELSE '' END,
                    CASE WHEN event_teams   THEN 'Teams, '   ELSE '' END
                ) AS competitions 
    FROM events ORDER BY event_start_date DESC")
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(rows, columns=cols)
except Exception as e:
    st.error(f"Error loading events: {e}")
    df = pd.DataFrame()
finally:
    cursor.close()
    conn.close()

admin_club_ids = get_admin_club_ids()
is_admin = bool(admin_club_ids)

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
            type_filter = st.selectbox("Event Type", ["All"] + sorted(df["event_type"].dropna().unique()))
        # Determine status options
        if admin_club_ids:
            # Admin user – show all statuses
            status_options = sorted(df["event_status"].dropna().unique())
        else:
            # Not admin – exclude 'Pending' and 'Cancelled'
            status_options = sorted(df[~df["event_status"].isin(["Pending", "Cancelled"])]["event_status"].dropna().unique())
        
        with col3:
            status_filter = st.selectbox("Event Status", ["All"] + status_options)
                        
            df_filtered = df.copy()
            
            # For non-admins, exclude Pending and Cancelled events
            if not is_admin:
                df_filtered = df_filtered[~df_filtered["event_status"].isin(["Pending", "Cancelled"])]

        if title_filter:
            df_filtered = df_filtered[df_filtered["event_title"].str.contains(title_filter, case=False, na=False)]
        if type_filter != "All":
            df_filtered = df_filtered[df_filtered["event_type"] == type_filter]
        if status_filter != "All":
            df_filtered = df_filtered[df_filtered["event_status"] == status_filter]

        if df_filtered.empty:
            st.info("No events found.")
        else:
            display_cols = [
                "id", "event_title", "event_type", "event_start_date", "event_end_date",
                "event_location", "event_status"
            ]
            df_display = df_filtered[display_cols].copy()
            df_display["event_start_date"] = pd.to_datetime(df_display["event_start_date"]).dt.strftime('%Y-%m-%d')
            df_display["event_end_date"] = pd.to_datetime(df_display["event_end_date"]).dt.strftime('%Y-%m-%d')
            
            selection = st.dataframe(
                df_display,
                selection_mode="single-row",
                on_select="rerun",
                hide_index=True,
                use_container_width=True,
                key="event_table"
            )

            selection_data = st.session_state.get("event_table")

            if (
                selection_data
                and "selection" in selection_data
                and selection_data["selection"].get("rows")
                and st.session_state.get("selected_event_id") is None
            ):
                row_index = selection_data["selection"]["rows"][0]
                selected_id = df_display.iloc[row_index]["id"]
                st.session_state.selected_event_id = selected_id
                st.rerun()

            new_event.add_new_event()

    else:
        st.button("🔙 Back to Event List", on_click=lambda: st.session_state.pop("selected_event_id"))

        selected_event = df[df["id"] == selected_event_id].iloc[0].to_dict()
        with st.spinner("Loading event details..."):
            if is_admin:
                TABS = st.tabs(["DETAILS", "REGISTER", "TABLES", "SCORES", "RESULT", "ADMIN"])
                PAGES = [Details, Register, Tables, Scores, Result, Admin]
            else:
                TABS = st.tabs(["DETAILS", "REGISTER", "TABLES", "SCORES", "RESULT"])
                PAGES = [Details, Register, Tables, Scores, Result]                
            for tab, page_module in zip(TABS, PAGES):
                with tab:
                    page_module.page(selected_event)

if st.session_state.get("test_mode"):
    from sidebar_utils import render_sidebar_widgets
    render_sidebar_widgets()
