import streamlit as st
import pandas as pd
import string
import random
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection

def page(selected_event):
    st.subheader("Event Admin")

    # Load events
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events_v ORDER BY EVENT_START_DATE DESC")
        df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
    except Exception as e:
        st.error(f"Error loading events: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    # Extract selected event details
    event_id = selected_event.get("ID")
    event_status = selected_event.get("EVENT_STATUS")
    user_email = selected_event.get("UPDATE_BY") or "admin@xabuteo.com"

    # Approve pending
    if event_status == "Pending":
        if st.button("✅ Approve"):
            try:
                conn = get_snowflake_connection()
                with conn.cursor() as cs:
                    cs.execute("""
                        UPDATE EVENTS
                        SET EVENT_STATUS = 'Approved',
                            UPDATE_TIMESTAMP = CURRENT_TIMESTAMP,
                            UPDATE_BY = %s
                        WHERE ID = %s
                    """, (user_email, event_id))
                    conn.commit()
                st.success("✅ Event status updated to 'Approved'.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to update: {e}")
            finally:
                conn.close()

    if event_status != "Cancelled":
        if st.button("❌ Cancel"):
            try:
                conn = get_snowflake_connection()
                with conn.cursor() as cs:
                    cs.execute("""
                        UPDATE EVENTS
                        SET EVENT_STATUS = 'Cancelled',
                            UPDATE_TIMESTAMP = CURRENT_TIMESTAMP,
                            UPDATE_BY = %s
                        WHERE ID = %s
                    """, (user_email, event_id))
                    conn.commit()
                st.success("❌ Event status updated to 'Cancelled'.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to cancel: {e}")
            finally:
                conn.close()

    # Seeding & Group Assignment
    with st.expander("➕ Seeding and Group Assignment", expanded=True):
        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, event_id, first_name, last_name, email,
                       club_name, club_code, seed_no, group_no
                FROM EVENT_REGISTRATION_V
                WHERE event_id = %s
                ORDER BY last_name, first_name
            """, (event_id,))
            df = pd.DataFrame(cursor.fetchall(), columns=[desc[0].upper() for desc in cursor.description])
        except Exception as e:
            st.error(f"Error loading registrations: {e}")
            return
        finally:
            cursor.close()
            conn.close()

        # Editable grid
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_column("SEED_NO", editable=True, type=["numericColumn"])
        gb.configure_column("GROUP_NO", editable=True)
        gb.configure_selection("multiple", use_checkbox=True)
        grid_response = AgGrid(
            df,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=True,
            theme="material"
        )

        updated_data = pd.DataFrame(grid_response["data"])
        if st.button("💾 Save Seeding/Grouping Changes"):
            try:
                updated_data = updated_data.reset_index(drop=True)
                df_orig = df.reset_index(drop=True)

                changed = updated_data.loc[
                    (updated_data["SEED_NO"] != df_orig["SEED_NO"]) |
                    (updated_data["GROUP_NO"] != df_orig["GROUP_NO"])
                ]

                if changed.empty:
                    st.warning("No changes detected.")
                else:
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()
                    for _, row in changed.iterrows():
                        cursor.execute("""
                            UPDATE EVENT_REGISTRATION
                            SET SEED_NO = %s, GROUP_NO = %s, UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                            WHERE USER_ID = %s AND EVENT_ID = %s
                        """, (
                            int(row["SEED_NO"] or 0),
                            row["GROUP_NO"] or '',
                            row["USER_ID"],
                            row["EVENT_ID"]
                        ))
                    conn.commit()
                    st.success(f"✅ {len(changed)} record(s) updated.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to save changes: {e}")
            finally:
                cursor.close()
                conn.close()

        # Grouping logic
        with st.form("auto_grouping_form"):
            num_groups = st.selectbox("Select number of groups", list(range(2, 11)), index=2)
            assign_btn = st.form_submit_button("🎯 Auto-Assign Groups")

            if assign_btn:
                try:
                    df["SEED_NO"] = pd.to_numeric(df["SEED_NO"], errors="coerce").fillna(0).astype(int)
                    seeded = df[df["SEED_NO"] > 0].sort_values("SEED_NO")
                    unseeded = df[df["SEED_NO"] == 0].sample(frac=1, random_state=42)

                    group_labels = list(string.ascii_uppercase[:num_groups])
                    groups = {label: [] for label in group_labels}

                    for i, (_, row) in enumerate(seeded.iterrows()):
                        group = group_labels[i % num_groups]
                        groups[group].append(row)

                    group_counts = {label: len(groups[label]) for label in group_labels}
                    for _, row in unseeded.iterrows():
                        smallest = min(group_counts, key=group_counts.get)
                        groups[smallest].append(row)
                        group_counts[smallest] += 1

                    final_rows = []
                    for label in group_labels:
                        for row in groups[label]:
                            row["GROUP_NO"] = label
                            final_rows.append(row)

                    final_df = pd.DataFrame(final_rows).sort_values(["GROUP_NO", "SEED_NO", "LAST_NAME"])
                    st.dataframe(final_df[["FIRST_NAME", "LAST_NAME", "SEED_NO", "GROUP_NO"]], use_container_width=True)

                    # Save group assignment
                    if st.button("💾 Save Assigned Groups"):
                        try:
                            conn = get_snowflake_connection()
                            cursor = conn.cursor()
                            for _, row in final_df.iterrows():
                                cursor.execute("""
                                    UPDATE EVENT_REGISTRATION
                                    SET GROUP_NO = %s,
                                        UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                                    WHERE user_id = %s AND event_id = %s
                                """, (
                                    row["GROUP_NO"],
                                    row["USER_ID"],
                                    row["EVENT_ID"]
                                ))
                            conn.commit()
                            st.success(f"✅ {len(final_df)} participants updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update groups: {e}")
                        finally:
                            cursor.close()
                            conn.close()
                except Exception as e:
                    st.error(f"❌ Grouping error: {e}")

    # Add new event
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
                        SELECT list_value FROM ref_lookup
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
            start_date = col1.date_input("Start Date")
            end_date = col2.date_input("End Date")

            col1, col2 = st.columns(2)
            reg_open = col1.date_input("Registration Open Date")
            reg_close = col2.date_input("Registration Close Date")

            location = st.text_input("Location")

            col1, col2, col3 = st.columns(3)
            event_open = col1.checkbox("Open")
            event_women = col1.checkbox("Women")
            event_junior = col2.checkbox("Junior")
            event_veteran = col2.checkbox("Veteran")
            event_teams = col3.checkbox("Teams")

            event_email = st.text_input("Contact Email")
            comments = st.text_area("Comments")

            if st.form_submit_button("Add Event"):
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
                        start_date, end_date,
                        reg_open, reg_close,
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
