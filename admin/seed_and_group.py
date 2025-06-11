import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection

def render(event_id):
    with st.expander("➕ Seeding and Group Assignment", expanded=True):
        # Persist selected competition
        if "selected_competition" not in st.session_state:
            st.session_state.selected_competition = "Open"

        try:
            conn = get_snowflake_connection()
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
                SELECT id, user_id, event_id, first_name, last_name, email,
                       club_name, club_code, seed_no, group_no
                FROM EVENT_REGISTRATION_V
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
        header_height = 113
        grid_height = min(row_count, max_rows_to_show) * row_height + header_height
        
        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            height=grid_height,
            theme="material"
        )

        updated_data = pd.DataFrame(grid_response["data"])
        if st.button("💾 Save Seeding/Grouping Changes"):
            try:
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
                            seed_no = 0
                        group_no = str(row["GROUP_NO"]) if row["GROUP_NO"] is not None else ''
                        record_id = row["ID"]
                        cursor.execute("""
                            UPDATE EVENT_REGISTRATION
                            SET SEED_NO = %s,
                                GROUP_NO = %s,
                                UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                            WHERE ID = %s
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
