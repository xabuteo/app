import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils import get_snowflake_connection

def render(event_id):
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
                        cursor.execute("""
                            UPDATE EVENT_REGISTRATION
                            SET SEED_NO = %s,
                                GROUP_NO = %s,
                                UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                            WHERE USER_ID = %s AND EVENT_ID = %s
                        """, (
                            seed_no,
                            group_no,
                            row["USER_ID"],
                            row["EVENT_ID"]
                        ))
                    conn.commit()
                    st.success(f"✅ {len(changed_rows)} record(s) updated.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to update: {e}")
            finally:
                cursor.close()
                conn.close()
