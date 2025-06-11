import streamlit as st
import pandas as pd
import string
from utils import get_snowflake_connection

def render(event_id, user_email):
    with st.expander("🎯 Auto Grouping"):
        # Persist selected competition in session state
        if "selected_competition" not in st.session_state:
            st.session_state.selected_competition = "Open"

        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()

            # Fetch competition types
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
                key="competition_selector_auto_group"
            )
            st.session_state.selected_competition = selected_comp

            # Load registrations for selected competition
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
            st.info("No registrations for this competition.")
            return

        num_groups = st.selectbox("Select number of groups", list(range(2, 11)), index=2)

        if st.button("🎲 Auto-Assign Competitors to Groups"):
            try:
                df_copy = df.copy()
                df_copy["SEED_NO"] = pd.to_numeric(df_copy["SEED_NO"], errors="coerce").fillna(0).astype(int)

                seeded = df_copy[df_copy["SEED_NO"] > 0].sort_values("SEED_NO")
                unseeded = df_copy[df_copy["SEED_NO"] == 0].sample(frac=1)

                group_labels = list(string.ascii_uppercase[:num_groups])
                groups = {label: [] for label in group_labels}

                # Round-robin assign seeded
                for idx, (_, row) in enumerate(seeded.iterrows()):
                    group = group_labels[idx % num_groups]
                    groups[group].append(row)

                # Distribute unseeded evenly
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
                st.session_state.final_group_df = final_df

                st.success("✅ Groups assigned. Review below:")
                st.dataframe(final_df[["FIRST_NAME", "LAST_NAME", "SEED_NO", "GROUP_NO"]], use_container_width=True)

            except Exception as e:
                st.error(f"❌ Grouping error: {e}")

        # Save to DB
        if "final_group_df" in st.session_state and st.session_state.final_group_df is not None:
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
                            WHERE id = %s
                        """, (
                            row["GROUP_NO"],
                            row["ID"]
                        ))
                    conn.commit()
                    st.success(f"✅ {len(final_df)} participants updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to update: {e}")
                finally:
                    cursor.close()
                    conn.close()
