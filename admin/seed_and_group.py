import streamlit as st
import pandas as pd
from utils import get_db_connection

def render(event_id):
    with st.expander("➕ Seeding and Group Assignment", expanded=False):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT group_no, seed_no, first_name, last_name, club_code, id, user_id, event_id
                FROM event_registration_v
                WHERE event_id = %s
                ORDER BY last_name, first_name
            """, (event_id,))
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]  # lowercase columns expected
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

        # Copy full df for update reference
        df_full = df.copy()

        # Columns to hide from user editing (ids)
        hidden_cols = ["id", "user_id", "event_id"]
        # Columns editable by user
        editable_cols = ["group_no", "seed_no"]
        # Columns to show in data_editor
        display_cols = [col for col in df.columns if col not in hidden_cols]

        df_display = df[display_cols]

        # Configure columns for st.data_editor
        col_config = {
            "group_no": st.column_config.TextColumn("Group No"),
            "seed_no": st.column_config.NumberColumn("Seed No", min_value=0, step=1, format="%d"),
        }

        # Disable all columns except editable ones
        disabled_cols = [col for col in df_display.columns if col not in editable_cols]

        edited_df = st.data_editor(
            df_display,
            column_config=col_config,
            disabled=disabled_cols,
            use_container_width=True,
            hide_index=True,
            key="seed_group_editor"
        )

        if st.button("💾 Save Seeding/Grouping Changes"):
            # Combine edited data with IDs for DB update
            updated_df = edited_df.copy()
            updated_df["id"] = df_full["id"]

            # Find changed rows by comparing with original df
            changed_mask = (
                (updated_df["seed_no"] != df_full["seed_no"]) |
                (updated_df["group_no"] != df_full["group_no"])
            )

            changed_rows = updated_df[changed_mask]

            if changed_rows.empty:
                st.warning("No changes detected.")
            else:
                try:
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
                    st.error(f"❌ Failed to update records: {e}")
                finally:
                    cursor.close()
                    conn.close()
