import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, get_userid

def page(selected_event):
    event_status = selected_event.get("EVENT_STATUS", "")
    event_id = selected_event.get("ID")
    user_id = get_userid()

    with st.expander(f"📋 Event Registration Form — Status: {event_status}", expanded=(event_status == "Open")):
        st.subheader(selected_event.get("EVENT_TITLE", "Untitled Event"))
        eventtype = selected_event.get("EVENT_TYPE", "")
        st.markdown(f"**{eventtype}**")

        reg_open = selected_event.get("REG_OPEN_DATE", "")
        reg_close = selected_event.get("REG_CLOSE_DATE", "")
        st.markdown(f"**Registration Dates:** {reg_open} to {reg_close}")

        if event_status == "Open":
            # Competition flags from event setup
            event_open = selected_event.get("EVENT_OPEN", False)
            event_women = selected_event.get("EVENT_WOMEN", False)
            event_junior = selected_event.get("EVENT_JUNIOR", False)
            event_veteran = selected_event.get("EVENT_VETERAN", False)
            event_teams = selected_event.get("EVENT_TEAMS", False)

            event_start_date = pd.to_datetime(selected_event.get("EVENT_START_DATE")).date()

            # Fetch player info
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT first_name, last_name, date_of_birth, gender, club_id, club_name
                    FROM player_club_v
                    WHERE id = %s
                      AND player_status = 'Approved'
                      AND %s BETWEEN valid_from AND valid_to
                    LIMIT 1
                """, (user_id, event_start_date))
                player = cursor.fetchone()
            except Exception as e:
                st.error(f"Error loading club info: {e}")
                return
            finally:
                cursor.close()
                conn.close()

            if not player:
                st.info("ℹ️ You are not assigned to any club at the event start date.")
                return

            first_name, last_name, dob, gender, club_id, club_name = player
            dob = pd.to_datetime(dob).date()
            gender = gender.upper()
            age = event_start_date.year - dob.year - ((event_start_date.month, event_start_date.day) < (dob.month, dob.day))

            st.markdown(f"👤 **Name:** {first_name} {last_name}")
            st.markdown(f"🏟️ **Club at Event Start Date:** {club_name}")

            competitions = {
                "Open": event_open,
                "Women": event_women and gender == "F",
                "Junior": event_junior and age < 18,
                "Veteran": event_veteran and age >= 45,
                "Teams": event_teams
            }

            st.markdown("### 🏆 Eligible Competitions")
            selected_competitions = [
                comp for comp, eligible in competitions.items()
                if eligible and st.checkbox(f"{comp} Competition")
            ]

            if st.button("📝 Register for Event"):
                try:
                    conn = get_snowflake_connection()
                    cs = conn.cursor()

                    for comp in selected_competitions:
                        cs.execute("""
                            INSERT INTO event_registration (
                                user_id, event_id, club_id, competition_type,
                                updated_timestamp, updated_by
                            )
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                        """, (
                            user_id, event_id, club_id, comp, user_id
                        ))

                    conn.commit()

                    st.success(f"✅ Registered for: {', '.join(selected_competitions)}")
                except Exception as e:
                    st.error(f"❌ Failed to register: {e}")
                finally:
                    cs.close()
                    conn.close()

    # ✅ Second expander: show registration view
    with st.expander(f"📑 View Registered Competitiors", expanded=(event_status in ("Closed", "Complete"))):
        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, email, first_name, last_name, club_name,
                       register_open, register_women, register_junior, register_veteran, register_teams
                FROM EVENT_REGISTRATION_V
                WHERE EVENT_ID = %s
                ORDER BY updated_timestamp DESC
            """, (event_id,))
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=cols)
        except Exception as e:
            st.error(f"❌ Failed to load registrations: {e}")
            return
        finally:
            cursor.close()
            conn.close()
    
        # Mapping of competitions to event and registration columns
        competition_config = {
            "Open":     ("EVENT_OPEN",     "REGISTER_OPEN"),
            "Women":    ("EVENT_WOMEN",    "REGISTER_WOMEN"),
            "Junior":   ("EVENT_JUNIOR",   "REGISTER_JUNIOR"),
            "Veteran":  ("EVENT_VETERAN",  "REGISTER_VETERAN"),
            "Teams":    ("EVENT_TEAMS",    "REGISTER_TEAMS"),
        }
    
        for comp, (event_flag, reg_col) in competition_config.items():
            if selected_event.get(event_flag):
                # Only include rows where the person registered for this competition
                comp_df = df[df[reg_col] == True][["USER_ID", "EMAIL", "FIRST_NAME", "LAST_NAME", "CLUB_NAME"]]
                if not comp_df.empty:
                    st.markdown(f"### 🏆 {comp} Competition ({len(comp_df)} registered)")
                    st.dataframe(comp_df, use_container_width=True)
    
                    # Add CSV download
                    csv = comp_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label=f"⬇️ Download {comp} Registrations as CSV",
                        data=csv,
                        file_name=f"{comp.lower()}_registrations_event_{event_id}.csv",
                        mime="text/csv"
                    )
