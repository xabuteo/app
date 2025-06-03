import streamlit as st
import pandas as pd
from utils import get_snowflake_connection

# in detail.py
def page(selected_event):
    with st.container(border=True):
        # Header and subheader
        st.subheader(selected_event.get("EVENT_TITLE", "Untitled Event"))
        eventtype = selected_event.get("EVENT_TYPE", "")
        st.markdown(f"**{eventtype}**")
    
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
            # Define all event competition flags early
            event_open = selected_event.get("EVENT_OPEN", False)
            event_women = selected_event.get("EVENT_WOMEN", False)
            event_junior = selected_event.get("EVENT_JUNIOR", False)
            event_veteran = selected_event.get("EVENT_VETERAN", False)
            event_teams = selected_event.get("EVENT_TEAMS", False)
        
            # Get current user's email from session
            current_email = st.user.email
        
            # Get and parse event start date
            event_start_date_str = selected_event.get("EVENT_START_DATE")
            event_start_date = pd.to_datetime(event_start_date_str).date()
        
            # Fetch player & club info from player_club_v
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT first_name, last_name, date_of_birth, gender, club_id, club_name
                    FROM player_club_v
                    WHERE email = %s
                      AND player_status = 'Approved'
                      AND %s BETWEEN valid_from AND valid_to
                    LIMIT 1
                """, (current_email, event_start_date))
                player = cursor.fetchone()
                cursor.close()
                conn.close()
            except Exception as e:
                st.error(f"Error loading club info: {e}")
                #return
        
            if not player:
                st.info("ℹ️ You are not assigned to any club at the event start date. Registration is not available.")
                #return
        
            # Unpack player record
            first_name, last_name, date_of_birth, gender, club_id, club_name = player
            date_of_birth = pd.to_datetime(date_of_birth).date()
            gender = gender.upper()
            age = event_start_date.year - date_of_birth.year - ((event_start_date.month, event_start_date.day) < (date_of_birth.month, date_of_birth.day))
        
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
                        id, event_id, club_id,
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
