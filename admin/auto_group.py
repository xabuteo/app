import streamlit as st
import pandas as pd
import string
import render
from utils import get_snowflake_connection

def auto_assign_groups(df, event_id):
    st.subheader("🎯 Auto-Assign Groups")

    num_groups = st.selectbox("Select number of groups", list(range(2, 11)), index=2)
    if st.button("🚀 Assign Groups Now"):
        try:
            df_copy = df.copy()
            df_copy["SEED_NO"] = pd.to_numeric(df_copy["SEED_NO"], errors="coerce").fillna(0).astype(int)

            seeded = df_copy[df_copy["SEED_NO"] > 0].sort_values("SEED_NO")
            unseeded = df_copy[df_copy["SEED_NO"] == 0].sample(frac=1, random_state=None)

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

            st.session_state["auto_group_df"] = final_df
            st.success("✅ Groups assigned. Review below before saving.")
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
                    st.success(f"✅ {len(final_df)} participants updated in EVENT_REGISTRATION.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save group assignments: {e}")
                finally:
                    cursor.close()
                    conn.close()

        except Exception as e:
            st.error(f"❌ Grouping failed: {e}")
