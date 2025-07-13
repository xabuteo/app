import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_db_connection

def render(event_id):
    with st.expander("➕ Seeding and Group Assignment", expanded=False):
        # Persist selected competition
        if "selected_competition" not in st.session_state:
            st.session_state.selected_competition = "Open"

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get competition list
            cursor.execute("""
                SELECT DISTINCT competition_type
                FROM event_registration
                WHERE event_id = %s
                ORDER BY competition_type
            """, (event_id,))
            competitions = [row[0] for row in cursor.fetchall()]
            if not competitions:
                st.info("No competitions found.")
                return

            selected_comp = st.radio(
                "🏆 Select Competition",
                competitions,
                index=competitions.index(st.session_state.selected_competition)
                    if st.session_state.selected_competition in competitions else 0,
                key="competition_selector_seed_group"
            )
            st.session_state.selected_competition = selected_comp

            cursor.execute("""
                SELECT group_no, seed_no, first_name, last_name, club_code, id, user_id, event_id
                FROM event_registration_v
                WHERE event_id = %s AND competition_type = %s
                ORDER BY last_name, first_name
            """, (event_id, selected_comp))
            rows = cursor.fetchall()
            cols = [desc[0].upper() for desc in cursor.description]
            df = pd.DataFrame(rows, columns=cols)
        except Exception as e:
            st.error(f"Error loading registrations: {e}")
            return
        finally:
            cursor.close()
            conn.close()

        if df.empty:
            st.info("No registrations found for this competition.")
            return

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(editable=False)
        gb.configure_column("SEED_NO", editable=True, type=["numericColumn"])
        gb.configure_column("GROUP_NO", editable=True, cellEditor="agTextCellEditor")
        gb.configure_selection("multiple", use_checkbox=True)
        grid_options = gb.build()

        row_count = len(df)
        max_rows_to_show = 10
        row_height = 48
        header_height = 64
        grid_height = min(row_count, max_rows_to_show) * row_height + header_height
        
        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            height=grid_height,
            theme="alpine"
        )

        updated_data = pd.DataFrame(grid_response["data"])
        if st.button("💾 Save Seeding/Grouping Changes"):
            try:
                updated_data_reset = updated_data.reset_index(drop=True)
                df_reset = df.reset_index(drop=True)

                changed_rows = updated_data_reset.loc[
                    (updated_data_reset["seed_no"] != df_reset["seed_no"]) |
                    (updated_data_reset["group_no"] != df_reset["group_no"])
                ]

                if changed_rows.empty:
                    st.warning("No changes detected.")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    for _, row in changed_rows.iterrows():
                        try:
                            seed_no = int(row["seed_no"])
                        except (ValueError, TypeError):
                            seed_no = 0
                        group_no = str(row["group_no"]) if row["group_no"] is not None else ''
                        record_id = row["id"]
                        cursor.execute("""
                            UPDATE event_registration
                            SET seed_no = %s,
                                group_no = %s,
                                updated_timestamp = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (
                            seed_no,
                            group_no,
                            record_id
                        ))
                    conn.commit()
                    st.success(f"✅ {len(changed_rows)} record(s) updated.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to update: {e}")
            finally:
                cursor.close()
                conn.close()
