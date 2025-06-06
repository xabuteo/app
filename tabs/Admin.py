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

    # Seeding and Group Assignment
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
            rows = cursor.fetchall()
            cols = [desc[0].upper() for desc in cursor.description]
            df = pd.DataFrame(rows, columns=cols)
        except Exception as e:
            st.error(f"Error loading registrations: {e}")
            return
        finally:
            cursor.close()
            conn.close()

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(editable=False)
        gb.configure_column("SEED_NO", editable=True, type=["numericColumn"])
        gb.configure_column("GROUP_NO", editable=True, cellEditor="agTextCellEditor")
        gb.configure_selection("multiple", use_checkbox=True)
        grid_options = gb.build()

        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            theme="material"
        )

        updated_data = pd.DataFrame(grid_response["data"])
        if st.button("💾 Save Seeding/Grouping Changes"):
            try:
                # Reset index for both to align rows correctly
                updated_data_reset = updated_data.reset_index(drop=True)
                df_reset = df.reset_index(drop=True)

                changed_rows = updated_data_reset.loc[
                    (updated_data_reset["SEED_NO"] != df_reset["SEED_NO"]) |
                    (updated_data_reset["GROUP_NO"] != df_reset["GROUP_NO"])
                ]
                if changed_rows.empty:
                    st.warning("No changes detected.")
                else:
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()
                    for _, row in changed_rows.iterrows():
                        try:
                            seed_no = int(row["SEED_NO"])
                        except (ValueError, TypeError):
                            seed_no = 0  # default if invalid
                        group_no = str(row["GROUP_NO"]) if row["GROUP_NO"] is not None else ''
                
        # Auto-grouping section
        with st.form("group_auto_assign"):
            num_groups = st.selectbox("Select number of groups", list(range(2, 11)), index=2)
            assign_btn = st.form_submit_button("🎯 Auto-Assign Groups")

            if assign_btn:
                try:
                    df_copy = df.copy()
                    df_copy["SEED_NO"] = pd.to_numeric(df_copy["SEED_NO"], errors="coerce").fillna(0).astype(int)

                    seeded = df_copy[df_copy["SEED_NO"] > 0].sort_values("SEED_NO")
                    unseeded = df_copy[df_copy["SEED_NO"] == 0].sample(frac=1, random_state=42)

                    group_labels = list(string.ascii_uppercase[:num_groups])
                    groups = {label: [] for label in group_labels}

                    for idx, (_, row) in enumerate(seeded.iterrows()):
                        group = group_labels[idx % num_groups]
                        groups[group].append(row)

                    total_unseeded = len(unseeded)
                    base_size = total_unseeded // num_groups
                    extras = total_unseeded % num_groups

                    idx = 0
                    for i, label in enumerate(group_labels):
                        size = base_size + (1 if i < extras else 0)
                        for _ in range(size):
                            groups[label].append(unseeded.iloc[idx])
                            idx += 1

                    final_rows = []
                    for label in group_labels:
                        for row in groups[label]:
                            row["GROUP_NO"] = label
                            final_rows.append(row)

                    final_df = pd.DataFrame(final_rows).sort_values(["GROUP_NO", "SEED_NO", "LAST_NAME"])
                    st.success("✅ Groups assigned successfully.")
                    st.dataframe(final_df[["FIRST_NAME", "LAST_NAME", "SEED_NO", "GROUP_NO"]], use_container_width=True)

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
                            st.success(f"✅ {len(final_df)} participants updated with group assignment.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update: {e}")
                        finally:
                            cursor.close()
                            conn.close()
                except Exception as e:
                    st.error(f"❌ Grouping error: {e}")
                    
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
