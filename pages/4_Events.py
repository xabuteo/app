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

    selected_rows = grid_response["selected_rows"]

    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict(orient="records")

    if selected_rows and isinstance(selected_rows, list) and len(selected_rows) > 0:
        selected_id = selected_rows[0].get("ID")
        selected_event = df[df["ID"] == selected_id].iloc[0].to_dict()

        with st.container(border=True):
            # Header and subheader
            st.subheader(selected_event.get("EVENT_TITLE", "Untitled Event"))
            eventtype = selected_event.get("EVENT_TYPE", "")
            st.markdown(f"**{eventtype}**")

            col1, col2 = st.columns(2)
            with col1:
                # Date display logic
                start_date = selected_event.get("EVENT_START_DATE", "")
                end_date = selected_event.get("EVENT_END_DATE", "")
                if start_date == end_date or not end_date:
                    date_str = f"**Date:** {start_date}"
                else:
                    date_str = f"**Date:** {start_date} to {end_date}"
    
                # Location
                location = selected_event.get("EVENT_LOCATION", "Unknown Location")
    
                # Display main event info
                st.markdown(date_str)
                st.markdown(f"**Location:** {location}")
            with col2:
                # Competitions
                competition = selected_event.get("COMPETITIONS", "Unknown")
    
                # Display main event info
                st.markdown(f"**Competitions:** {competition}")
        
            # Registration expander
            with st.expander("📋 Registration Details", expanded=True):
                reg_open = selected_event.get("REG_OPEN_DATE", "")
                reg_close = selected_event.get("REG_CLOSE_DATE", "")
                event_status = selected_event.get("EVENT_STATUS", "")

                st.markdown(f"**Registration Dates:** {reg_open} to {reg_close}")
                st.markdown(f"**Status:** {event_status}")

                # Approve logic
                event_id = selected_event.get("ID")
                user_email = st.session_state.get("user", {}).get("email", "unknown@user.com")

                if event_status == "Pending":
                    if st.button("✅ Approve"):
                        try:
                            conn = get_snowflake_connection()
                            cs = conn.cursor()
                            update_sql = """
                                UPDATE EVENTS
                                SET EVENT_STATUS = 'Approved',
                                    UPDATE_TIMESTAMP = CURRENT_TIMESTAMP,
                                    UPDATE_BY = %s
                                WHERE ID = %s
                            """
                            cs.execute(update_sql, (user_email, event_id))
                            conn.commit()
                            st.success("✅ Event status updated to 'Approved'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update event status: {e}")
                        finally:
                            cs.close()
                            conn.close()
                
                elif event_status == "Open":
                    st.markdown("🔓 Registration section")
                
                    # Get current user's email from session
                    current_email = st.user.email
                    event_start_date_str = selected_event.get("EVENT_START_DATE")
                    event_start_date = pd.to_datetime(event_start_date_str).date()

                    # Fetch player & club info from player_club_v
                    try:
                        conn = get_snowflake_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT first_name, last_name, dob, gender, club_id, club_name
                            FROM player_club_v
                            WHERE user_id = %s
                              AND player_status = 'Approved'
                              AND %s BETWEEN valid_from AND valid_to
                            LIMIT 1
                        """, (current_email, event_start_date))
                        player = cursor.fetchone()
                        cursor.close()
                        conn.close()
                    except Exception as e:
                        st.error(f"Error loading club info: {e}")
                        return
                
                    if not player:
                        st.info("ℹ️ You are not assigned to any club at the event start date. Registration is not available.")
                        return
                
                    # Unpack player record
                    first_name, last_name, dob, gender, club_id, club_name = player
                    dob = pd.to_datetime(dob).date()
                    gender = gender.upper()
                    age = event_start_date.year - dob.year - ((event_start_date.month, event_start_date.day) < (dob.month, dob.day))
                
                    st.markdown(f"👤 **Name:** {first_name} {last_name}")
                    st.markdown(f"🏟️ **Club at Event Start Date:** {club_name}")
                
                    # Determine eligibility
                    competitions = {
                        "Open": event_open,
                        "Women": event_women and gender == "F",
                        "Junior": event_junior and age < 18,
                        "Veteran": event_veteran and age >= 45,
                        "Teams": event_teams
                    }
                
                    st.markdown("### 🏆 Eligible Competitions")
                    comp_checkboxes = {}
                    for comp, eligible in competitions.items():
                        if eligible:
                            comp_checkboxes[comp] = st.checkbox(f"{comp} Competition")
                
                    if st.button("📝 Register for Event"):
                        try:
                            conn = get_snowflake_connection()
                            cs = conn.cursor()
                            cs.execute("""
                                INSERT INTO event_registration (
                                    user_id, event_id, club_id,
                                    register_open, register_women, register_junior, register_veteran, register_teams,
                                    update_timestamp, update_by
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                            """, (
                                user_id, event_id, club_id,
                                comp_checkboxes.get("Open", False),
                                comp_checkboxes.get("Women", False),
                                comp_checkboxes.get("Junior", False),
                                comp_checkboxes.get("Veteran", False),
                                comp_checkboxes.get("Teams", False),
                                user_email
                            ))
                            conn.commit()
                            st.success("✅ Registered successfully.")
                        except Exception as e:
                            st.error(f"❌ Failed to register: {e}")
                        finally:
                            cs.close()
                            conn.close()

                if not event_status == "Cancelled":                    
                    if st.button("❌ Cancel"):
                        try:
                            conn = get_snowflake_connection()
                            cs = conn.cursor()
                            update_sql = """
                                UPDATE EVENTS
                                SET EVENT_STATUS = 'Cancelled',
                                    UPDATE_TIMESTAMP = CURRENT_TIMESTAMP,
                                    UPDATE_BY = %s
                                WHERE ID = %s
                            """
                            cs.execute(update_sql, (user_email, event_id))
                            conn.commit()
                            st.success("❌ Event status updated to 'Cancelled'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update event status: {e}")
                        finally:
                            cs.close()
                            conn.close()
            
            # Email and comments
            st.markdown(f"**Contact Email:** {selected_event.get('EVENT_EMAIL', 'N/A')}")
            st.markdown(f"**Comments:** {selected_event.get('EVENT_COMMENTS', 'None')}")

    # Add new event
    with st.expander("➕ Add New Event"):
        with st.form("add_event_form"):
            col1, col2 = st.columns(2)
            with col1:            
                title = st.text_input("Event Title")
            with col2:            
                # Fetch event types from lookup table
                try:
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT list_value
                        FROM xabuteo.public.ref_lookup
                        WHERE list_type = 'event_type'
                        ORDER BY list_order
                    """)
                    event_types = [row[0] for row in cursor.fetchall()]
                except Exception as e:
                    st.error(f"Error loading event types: {e}")
                    event_types = []
                finally:
                    cursor.close()
                    conn.close()
        
                event_type = st.selectbox("Event Type", event_types)

            col1, col2 = st.columns(2)
            with col1:            
                start_date = st.date_input("Start Date")
            with col2:            
                end_date = st.date_input("End Date")

            col1, col2 = st.columns(2)
            with col1:            
                reg_open_date = st.date_input("Registration Open Date")
            with col2:            
                reg_close_date = st.date_input("Registration Close Date")
            
            location = st.text_input("Location")
    
            # Checkboxes
            col1, col2, col3 = st.columns(3)
            with col1:
                event_open = st.checkbox("Open")
                event_women = st.checkbox("Women")
            with col2:
                event_junior = st.checkbox("Junior")
                event_veteran = st.checkbox("Veteran")
            with col3:
                event_teams = st.checkbox("Teams")

            event_email = st.text_input("Contact Email")
    
            comments = st.text_area("Comments")
    
            submit = st.form_submit_button("Add Event")
    
            if submit:
                try:
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO xabuteo.public.events (
                            event_title, event_type, event_location,
                            event_start_date, event_end_date,
                            reg_open_date, reg_close_date,
                            event_email, event_open, event_women,
                            event_junior, event_veteran, event_teams,
                            event_comments
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        title, event_type, location,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        reg_open_date.strftime('%Y-%m-%d'),
                        reg_close_date.strftime('%Y-%m-%d'),
                        event_email, event_open, event_women,
                        event_junior, event_veteran, event_teams,
                        comments
                    ))
                    conn.commit()
                    st.success("✅ Event added successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error inserting event: {e}")
                finally:
                    cursor.close()
                    conn.close()

show()
