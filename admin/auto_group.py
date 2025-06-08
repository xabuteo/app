# admin/auto_group.py

import streamlit as st
import pandas as pd
import string
from utils import get_snowflake_connection

def render(event_id, user_email):
#    st.markdown("### 🎯 Auto-Assign Groups")
    with st.expander("🎯 Auto-Assign Groups"):
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
    
        if df.empty:
            st.warning("No registrations found.")
            return
    
        num_groups = st.selectbox("Select number of groups", list(range(2, 11)), index=2)
        if st.button("🎯 Auto-Assign Groups Now"):
            try:
                df_copy = df.copy()
                df_copy["SEED_NO"] = pd.to_numeric(df_copy["SEED_NO"], errors="coerce").fillna(0).astype(int)
    
                seeded = df_copy[df_copy["SEED_NO"] > 0].sort_values("SEED_NO")
                unseeded = df_copy[df_copy["SEED_NO"] == 0].sample(frac=1, random_state=None)  # random shuffle
    
                group_labels = list(string.ascii_uppercase[:num_groups])
                groups = {label: [] for label in group_labels}
    
                for idx, (_, row) in enumerate(seeded.iterrows()):
                    group = group_labels[idx % num_groups]
                    groups[group].append(row)
    
                group_counts = {label: len(groups[label]) for label in group_labels}
                for _, row in unseeded.iterrows():
                    smallest_group = min(group_counts, key=group_counts.get)
                    groups[smallest_group].append(row)
                    group_counts[smallest_group] += 1
    
                final_rows = []
                for label in group_labels:
                    for row in groups[label]:
                        row["GROUP_NO"] = label
                        final_rows.append(row)
    
                final_df = pd.DataFrame(final_rows).sort_values(["GROUP_NO", "SEED_NO", "LAST_NAME"])
    
                st.session_state.final_group_df = final_df
                st.dataframe(final_df[["FIRST_NAME", "LAST_NAME", "SEED_NO", "GROUP_NO"]], use_container_width=True)
                
                # Ensure final_df is available
                if "final_group_df" in st.session_state and not st.session_state.final_group_df.empty:
                    final_df = st.session_state.final_group_df
                
                    if st.button("💾 Save Assigned Groups to DB"):
                        try:
                            conn = get_snowflake_connection()
                            cursor = conn.cursor()
                            for _, row in final_df.iterrows():
                                cursor.execute("""
                                    UPDATE EVENT_REGISTRATION
                                    SET GROUP_NO = %s,
                                        UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                                    WHERE USER_ID = %s AND EVENT_ID = %s
                                """, (
                                    row["GROUP_NO"],
                                    row["USER_ID"],
                                    row["EVENT_ID"]
                                ))
                            conn.commit()
                            st.success(f"✅ {len(final_df)} participants updated with group assignment.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to save to database: {e}")
                        finally:
                            cursor.close()
                            conn.close()
                else:
                    st.warning("No group assignments available to save.")
