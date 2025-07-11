import streamlit as st
import pandas as pd
from utils import get_db_connection, get_userid
from datetime import datetime, date, timedelta

def page(selected_event):
    today = date.today() 
    temp_status = selected_event.get("event_status", "")
    event_id = selected_event.get("id")
    user_id = get_userid()
    reg_open = selected_event.get("reg_open_date", "")
    reg_close = selected_event.get("reg_close_date", "")

    event_status = (
        "Open"   if temp_status == "Approved" and reg_open <= today <= reg_close else
        "Closed" if temp_status == "Approved" and today >  reg_close            else
        event_status
    )
    
    with st.expander(f"📋 Event Registration Form — Status: {event_status}", expanded=(event_status == "Open")):
        st.subheader(selected_event.get("event_title", "Untitled Event"))
        eventtype = selected_event.get("event_type", "")
        st.markdown(f"**{eventtype}**")

        st.markdown(f"**Registration Dates:** {reg_open} to {reg_close}")

        if event_status == "Open":
            # Competition flags from event setup
            event_open = selected_event.get("event_open", False)
            event_women = selected_event.get("event_women", False)
            event_junior = selected_event.get("event_junior", False)
            event_veteran = selected_event.get("event_veteran", False)
            event_teams = selected_event.get("event_teams", False)

            event_start_date = pd.to_datetime(selected_event.get("event_start_date")).date()

            # Fetch player info
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT first_name, last_name, date_of_birth, gender, club_id, club_name
                    FROM player_club_v
                    WHERE id = %s
                      AND player_status in ('Active', 'Approved')
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
                if not selected_competitions:
                    st.warning("Please select at least one competition to register.")
                    return
            
                try:
                    conn = get_db_connection()
                    cs = conn.cursor()
            
                    registered_comps = []
            
                    for comp in selected_competitions:
                        # Check if already registered
                        cs.execute("""
                            SELECT 1
                            FROM event_registration
                            WHERE user_id = %s
                              AND event_id = %s
                              AND competition_type = %s
                            LIMIT 1
                        """, (user_id, event_id, comp))
            
                        exists = cs.fetchone()
                        if exists:
                            st.warning(f"⚠️ Already registered for {comp} competition.")
                            continue
            
                        # Insert new registration
                        cs.execute("""
                            INSERT INTO event_registration (
                                user_id, event_id, club_id, competition_type,
                                updated_timestamp, updated_by
                            )
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                        """, (
                            user_id, event_id, club_id, comp, user_id
                        ))
                        registered_comps.append(comp)
            
                    conn.commit()
            
                    if registered_comps:
                        st.success(f"✅ Registered for: {', '.join(registered_comps)}")
                    else:
                        st.info("ℹ️ No new registrations submitted.")
            
                except Exception as e:
                    st.error(f"❌ Failed to register: {e}")
                finally:
                    cs.close()
                    conn.close()

    # ✅ Second expander: show registration view
    with st.expander(f"📑 View Registered Competitors", expanded=(event_status in ("Closed", "Complete"))):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, email, first_name, last_name, club_name, competition_type
                FROM event_registration_v
                WHERE event_id = %s
                ORDER BY competition_type, last_name, first_name
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
    
        if df.empty:
            st.info("No registrations yet.")
        else:
            competitions = df["competition_type"].unique()
            for comp in competitions:
                comp_df = df[df["competition_type"] == comp][["user_id", "email", "first_name", "last_name", "club_name"]]
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

            # ✅ Populate test competitors button
            comp_to_copy = st.selectbox("Select competition to copy from test event (1001)", competitions)
            if st.button("🧪 Populate Test Competitors"):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(f"""
                        INSERT INTO event_registration(user_id, club_id, event_id, competition_type)
                        SELECT user_id, club_id, %s, %s
                        FROM event_registration
                        WHERE event_id = 1001 AND competition_type = %s
                    """, (event_id, comp_to_copy, comp_to_copy))
                    conn.commit()
                    st.success(f"✅ Test competitors for '{comp_to_copy}' added to event {event_id}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to populate test competitors: {e}")
                finally:
                    cursor.close()
                    conn.close()
