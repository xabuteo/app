import streamlit as st
import pandas as pd
import string
from contextlib import closing
from utils import get_db_connection

def render(event_id, user_email):
    with st.expander("🎯 Auto Grouping"):
        st.session_state.setdefault("selected_competition", "open")

        # ── 1. fetch competitions & registrations ────────────────────────
        try:
            conn = get_db_connection()
            cur  = conn.cursor()

            cur.execute("""
                SELECT DISTINCT competition_type
                FROM event_registration
                WHERE event_id = %s
                ORDER BY competition_type
            """, (event_id,))
            competitions = [r[0] for r in cur.fetchall()]
            if not competitions:
                st.info("No competitions found.")
                return

            selected_comp = st.radio(
                "🏆 Select Competition",
                competitions,
                index=competitions.index(st.session_state["selected_competition"])
                      if st.session_state["selected_competition"] in competitions else 0,
                key="competition_selector_auto_group"
            )
            st.session_state["selected_competition"] = selected_comp

            cur.execute("""
                SELECT id, user_id, event_id, first_name, last_name, email,
                       club_name, club_code, seed_no, group_no
                FROM event_registration_v
                WHERE event_id = %s AND competition_type = %s
                ORDER BY last_name, first_name
            """, (event_id, selected_comp))
            rows = cur.fetchall()
            cols = [d[0].lower() for d in cur.description]   # <-- keep lower‑case
            df   = pd.DataFrame(rows, columns=cols)
        except Exception as exc:
            st.error(f"Error loading registrations: {exc}")
            return
        finally:
            cur.close()
            conn.close()

        if df.empty:
            st.info("No registrations for this competition.")
            return

        # ── 2. UI controls ───────────────────────────────────────────────
        num_groups = st.selectbox("Select number of groups", list(range(2, 32)), index=2)

        # ── 3. Auto‑assign button logic ─────────────────────────────────
        if st.button("🎲 Auto‑Assign Competitors to Groups"):
            try:
                df_work = df.copy()
                df_work["seed_no"] = (
                    pd.to_numeric(df_work["seed_no"], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )

                seeded    = df_work[df_work["seed_no"] > 0].sort_values("seed_no")
                unseeded  = df_work[df_work["seed_no"] == 0].sample(frac=1)
                labels    = list(string.ascii_uppercase[:num_groups])
                buckets   = {lbl: [] for lbl in labels}

                # round‑robin the seeded players
                for i, (_, row) in enumerate(seeded.iterrows()):
                    buckets[labels[i % num_groups]].append(row)

                # then distribute unseeded to keep counts even
                counts = {lbl: len(buckets[lbl]) for lbl in labels}
                for _, row in unseeded.iterrows():
                    tgt = min(counts, key=counts.get)
                    buckets[tgt].append(row)
                    counts[tgt] += 1

                # flatten back out
                final_rows = []
                for lbl in labels:
                    for row in buckets[lbl]:
                        row["group_no"] = lbl
                        final_rows.append(row)

                final_df = (
                    pd.DataFrame(final_rows)
                    .sort_values(["group_no", "seed_no", "last_name"])
                    .reset_index(drop=True)
                )
                st.session_state.final_group_df = final_df

                # ── 4. Write back to DB ────────────────────────────────
                with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
                    for _, row in final_df.iterrows():
                        cur.execute("""
                            UPDATE event_registration
                            SET group_no = %s,
                                updated_timestamp = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (row["group_no"], row["id"]))
                    conn.commit()

                st.success(f"✅ {len(final_df)} participants assigned and saved to DB.")
                st.dataframe(
                    final_df[["first_name", "last_name", "seed_no", "group_no"]],
                    use_container_width=True
                )

            except Exception as exc:
                st.error(f"❌ Grouping or DB update error: {exc}")
