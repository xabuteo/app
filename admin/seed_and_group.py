import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_db_connection


# ──────────────────────────────────────────────────────────────────────────
def render(event_id: int) -> None:
    with st.expander("➕ Seeding and Group Assignment", expanded=False):
        # ── remember last competition the user looked at
        st.session_state.setdefault("selected_competition", "Open")

        # ── fetch competitions & registrations --------------------------------
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # competition list
            cur.execute(
                """SELECT DISTINCT competition_type
                   FROM event_registration
                   WHERE event_id = %s
                   ORDER BY competition_type""",
                (event_id,),
            )
            competitions = [r[0] for r in cur.fetchall()]
            if not competitions:
                st.info("No competitions found.")
                return

            # radio selector
            selected_comp = st.radio(
                "🏆 Select Competition",
                competitions,
                index=competitions.index(st.session_state["selected_competition"])
                if st.session_state["selected_competition"] in competitions
                else 0,
                key="competition_selector_seed_group",
            )
            st.session_state["selected_competition"] = selected_comp

            # fetch registrations view
            cur.execute(
                """SELECT group_no, seed_no, first_name, last_name,
                          club_code, id, user_id, event_id
                   FROM event_registration_v
                   WHERE event_id = %s AND competition_type = %s
                   ORDER BY last_name, first_name""",
                (event_id, selected_comp),
            )
            rows = cur.fetchall()
            cols = [d[0].upper() for d in cur.description]
            df_original = pd.DataFrame(rows, columns=cols)
        except Exception as exc:
            st.error(f"Error loading registrations: {exc}")
            return
        finally:
            cur.close()
            conn.close()

        # ── empty state -------------------------------------------------------
        if df_original.empty:
            st.info("No registrations found for this competition.")
            return

        # ── editable table ----------------------------------------------------
        hidden_cols = ["id", "user_id", "event_id"]
        editable_cols = ["group_no", "seed_no"]
        
        edited_df = st.data_editor(
            df_original,
            column_config={
                # editable columns
                "group_no": st.column_config.TextColumn("Group No"),
                "seed_no":  st.column_config.NumberColumn("Seed No", min_value=0, step=1, format="%d"),
                # hide the PK / FK columns
                **{col: st.column_config.Column(hidden=True) for col in hidden_cols},
            },
            disabled=[c for c in df_original.columns if c not in editable_cols],
            use_container_width=True,
            hide_index=True,
            key="seed_group_editor",
        )
        # ── save button & diff detection --------------------------------------
        if st.button("💾 Save Seeding / Grouping Changes"):
            # pandas aligns by index, so compare directly
            changed_mask = (
                (edited_df["SEED_NO"] != df_original["SEED_NO"])
                | (edited_df["GROUP_NO"] != df_original["GROUP_NO"])
            )
            changed_rows = edited_df.loc[changed_mask]

            if changed_rows.empty:
                st.warning("No changes detected.")
                return

            try:
                conn = get_db_connection()
                cur = conn.cursor()

                for _, row in changed_rows.iterrows():
                    # normalise values
                    seed_no = int(row["SEED_NO"]) if pd.notnull(row["SEED_NO"]) else 0
                    group_no = str(row["GROUP_NO"]) if pd.notnull(row["GROUP_NO"]) else ""

                    cur.execute(
                        """UPDATE event_registration
                           SET seed_no = %s,
                               group_no = %s,
                               updated_timestamp = CURRENT_TIMESTAMP
                           WHERE id = %s""",
                        (seed_no, group_no, row["ID"]),
                    )

                conn.commit()
                st.success(f"✅ {len(changed_rows)} record(s) updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"❌ Failed to update: {exc}")
            finally:
                cur.close()
                conn.close()
