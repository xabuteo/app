import streamlit as st
from utils import get_snowflake_connection, get_admin_club_ids

def add_new_event():
    club_ids = get_admin_club_ids()

    if not club_ids:
        # st.info("⛔ Only club admins can create events.")
        return

    with st.expander("➕ Add New Event"):
        with st.form("add_event_form"):
            # Fetch host clubs
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                format_ids = ",".join(["%s"] * len(club_ids))
                cursor.execute(
                    f"""
                    SELECT id, club_name
                    FROM clubs
                    WHERE id IN ({format_ids})
                    ORDER BY club_name
                    """, tuple(club_ids)
                )
                host_club_options = cursor.fetchall()
                club_id_to_name = {row[0]: row[1] for row in host_club_options}
                club_name_to_id = {v: k for k, v in club_id_to_name.items()}
            except Exception as e:
                st.error(f"Error loading clubs: {e}")
                return
            finally:
                cursor.close()
                conn.close()

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
            
            col1, col2 = st.columns(2)
            with col1:
                location = st.text_input("📍 Location")
            with col2:
                club_names = list(club_name_to_id.keys())
            
                if len(club_names) == 1:
                    selected_club_name = club_names[0]
                    st.markdown(f"🏟️ **Host Club:** {selected_club_name}")
                else:
                    selected_club_name = st.selectbox("🏟️ Host Club", club_names)
            
                host_club_id = club_name_to_id[selected_club_name]
                
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
                            event_comments, host_club_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        title, event_type, location,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        reg_open_date.strftime('%Y-%m-%d'),
                        reg_close_date.strftime('%Y-%m-%d'),
                        event_email, event_open, event_women,
                        event_junior, event_veteran, event_teams,
                        comments, host_club_id
                    ))
                    conn.commit()
                    st.success("✅ Event added successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to add event: {e}")
                finally:
                    cursor.close()
                    conn.close()
