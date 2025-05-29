import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def show():
    st.set_page_config(layout="wide")
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

    # --- Filters ---
    st.subheader("🔍 Search and Filter")
    col1, col2, col3 = st.columns(3)

    with col1:
        title_filter = st.text_input("Search by Title")

    with col2:
        type_filter = st.selectbox(
            "Event Type",
            options=["All"] + sorted(df["EVENT_TYPE"].dropna().unique().tolist()) if "EVENT_TYPE" in df.columns else ["All"]
        )

    with col3:
        status_filter = st.selectbox(
            "Event Status",
            options=["All"] + sorted(df["EVENT_STATUS"].dropna().unique().tolist()) if "EVENT_STATUS" in df.columns else ["All"]
        )

    # Apply filters
    if title_filter and "EVENT_TITLE" in df.columns:
        df = df[df["EVENT_TITLE"].str.contains(title_filter, case=False, na=False)]
    if type_filter != "All" and "EVENT_TYPE" in df.columns:
        df = df[df["EVENT_TYPE"] == type_filter]
    if status_filter != "All" and "EVENT_STATUS" in df.columns:
        df = df[df["EVENT_STATUS"] == status_filter]

    if df.empty:
        st.warning("No events match the filter.")
        return

    # --- Display table with st_aggrid ---
    display_cols = [
        "ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_START_DATE",
        "EVENT_END_DATE", "EVENT_LOCATION", "EVENT_STATUS"
    ]
    df_display = df[display_cols].copy()

    # Format dates
    df_display["EVENT_START_DATE"] = pd.to_datetime(df_display["EVENT_START_DATE"]).dt.date
    df_display["EVENT_END_DATE"] = pd.to_datetime(df_display["EVENT_END_DATE"]).dt.date

    st.markdown("### 📋 Event List")

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_column("ID", hide=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="streamlit",
        height=400,
        fit_columns_on_grid_load=True
    )

    selected = grid_response["selected_rows"]

    # --- Show full event details if a row is selected ---
    if selected and len(selected) > 0:
        selected_event_id = selected[0]["ID"]

        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM xabuteo.public.events_v WHERE ID = %s", (selected_event_id,))
            row = cursor.fetchone()

            if not row:
                st.warning("Event not found.")
            else:
                cols = [desc[0] for desc in cursor.description]
                event = dict(zip(cols, row))

                st.markdown("## 🧾 Event Details")

                for key, value in event.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")

                if st.button(f"📝 Register for '{event['EVENT_TITLE']}'"):
                    st.success(f"✅ You're registered for **{event['EVENT_TITLE']}**!")

        except Exception as e:
            st.error(f"Error loading event details: {e}")
        finally:
            cursor.close()
            conn.close()
