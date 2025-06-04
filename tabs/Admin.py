import streamlit as st
import pandas as pd
from utils import get_snowflake_connection

def page(selected_event):
    st.subheader("Event Admin")

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

    # Extract values from selected_event
    event_id = selected_event.get("ID")
    event_status = selected_event.get("EVENT_STATUS")
    user_email = selected_event.get("UPDATE_BY", "admin@xabuteo.com")  # fallback default

    # Approve pending event
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
                    
    # Add new event form
    with st.expander("➕ Add New Event"):
        with st.form("add_event_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Event Title")
            with col2:
                try:
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT list_value
                        FROM ref_lookup
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
                        INSERT INTO events (
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
