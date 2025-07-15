import streamlit as st
import pandas as pd
import string
import random
from contextlib import closing
from utils import get_db_connection

# ─────────────────────────────────────────────────────────────────────────────
def generate_knockout_placeholders(num_groups: int):
    """Return (round_type, group_no, p1_id, p2_id) rows for the given group count."""
    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            select round_type, group_no, p1_id, p2_id
            from knockout_matches
            where %s between min_group and max_group
            order by id
            """,
            (num_groups,),
        )
        return cur.fetchall()            # already tuples


# ─────────────────────────────────────────────────────────────────────────────
def update_knockout_placeholders(event_id: int) -> bool:
    """Replace placeholder IDs with real winners once scores are final."""
    sql_1 = """
        update event_matches em
        join event_ko_round_v ek
          on em.event_id = ek.event_id
         and em.competition_type = ek.competition_type
         and em.player_1_id = ek.placeholder_id
        set em.player_1_id = ek.player_id,
            em.player_1_club_id = ek.club_id,
            em.status = case when em.player_2_id > 0 then 'scheduled' else em.status end,
            em.updated_timestamp = current_timestamp
        where em.event_id = %s
          and em.status <> 'final'
    """
    sql_2 = sql_1.replace("player_1_", "player_2_")  # same join, swap side

    try:
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
            cur.execute(sql_1, (event_id,))
            cur.execute(sql_2, (event_id,))
            conn.commit()
        st.success("✅ knockout placeholders filled where possible.")
        return True
    except Exception as exc:
        st.error(f"❌ failed to replace knockout placeholders: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
def fetch_matches_df(event_id: int, comp: str) -> pd.DataFrame:
    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            select id, competition_type, round_no, group_no,
                   player1, player1_goals, player2_goals, player2
            from event_matches_v
            where event_id = %s and competition_type = %s
            order by round_no, group_no
            """,
            (event_id, comp),
        )
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]          # already lower‑case in view
        return pd.DataFrame(rows, columns=cols)


def render_match_table(event_id: int, comp: str):
    df_full = fetch_matches_df(event_id, comp)
    if df_full.empty:
        return None

    # hide the DB id from users but keep for updates
    df_display = df_full.drop(columns=["id", "competition_type"])

    edited = st.data_editor(
        df_display,
        column_config={
            "player1_goals": st.column_config.NumberColumn(
                label="P1 goals", min_value=0, step=1, format="%d"
            ),
            "player2_goals": st.column_config.NumberColumn(
                label="P2 goals", min_value=0, step=1, format="%d"
            ),
        },
        disabled=[
            c
            for c in df_display.columns
            if c not in ("player1_goals", "player2_goals")
        ],
        use_container_width=True,
        hide_index=True,
        key=f"match_editor_{event_id}_{comp}",
    )

    # bring back the ID so caller can update DB
    edited["id"] = df_full["id"]
    return edited


# ─────────────────────────────────────────────────────────────────────────────
def render_match_generation(event_id: int):
    with st.expander("🎾 match generation & scoring"):
        # ---------------------------------------------------------------- comp picker
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
            cur.execute(
                "select distinct competition_type from event_registration where event_id = %s",
                (event_id,),
            )
            competitions = [r[0] for r in cur.fetchall()]

        if not competitions:
            st.info("ℹ️ no competitions in this event.")
            return

        comp = st.radio("🏆 select competition", competitions, key="match_gen_comp")

        # ---------------------------------------------------------------- any matches yet?
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
            cur.execute(
                "select count(*) from event_matches where event_id = %s and competition_type = %s",
                (event_id, comp),
            )
            match_count = cur.fetchone()[0]

        # allow deletion / regeneration
        if match_count > 0 and st.button("🔁 re‑generate (delete old)"):
            with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
                cur.execute(
                    "delete from event_matches where event_id = %s and competition_type = %s",
                    (event_id, comp),
                )
                conn.commit()
            st.success("old matches deleted.")
            match_count = 0

        # ---------------------------------------------------------------- need group data
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
            cur.execute(
                """
                select id, user_id, club_id, group_no
                from event_registration
                where event_id = %s and group_no is not null and competition_type = %s
                """,
                (event_id, comp),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            reg_df = pd.DataFrame(rows, columns=cols)

        if reg_df.empty:
            st.info("ℹ️ no groupings yet.")
            return

        # ---------------------------------------------------------------- generate button
        if match_count == 0 and st.button("⚙️ generate round‑robin matches"):
            try:
                matches_to_insert = []
                # === round‑robin builder (unchanged logic, but lower‑case keys) ===
                groups = sorted(reg_df["group_no"].unique())
                max_round = 0

                for g in groups:
                    players = (
                        reg_df[reg_df["group_no"] == g]
                        .sort_values("id")
                        .to_dict("records")
                    )
                    if len(players) % 2:
                        players.append(
                            dict(id=None, user_id=-1, club_id=None, group_no=g)
                        )

                    n = len(players)
                    rounds = n - 1
                    max_round = max(max_round, rounds)
                    half = n // 2
                    rotation = players[:]

                    for r in range(1, rounds + 1):
                        for i in range(half):
                            p1, p2 = rotation[i], rotation[n - 1 - i]
                            matches_to_insert.append(
                                dict(
                                    event_id=event_id,
                                    competition_type=comp,
                                    group_no=g,
                                    round_type="group",
                                    round_no=r,
                                    player_1_id=p1["user_id"],
                                    player_1_club_id=p1["club_id"],
                                    player_2_id=p2["user_id"],
                                    player_2_club_id=p2["club_id"],
                                    status="scheduled",
                                )
                            )
                        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

                # === knockout placeholders ====================================
                ko_placeholders = generate_knockout_placeholders(len(groups))
                round_order = [
                    "barrage",
                    "round of 64",
                    "round of 32",
                    "round of 16",
                    "quarter‑final",
                    "semi‑final",
                    "final",
                ]
                order_map = {rt: i for i, rt in enumerate(round_order)}
                ko_placeholders.sort(key=lambda x: order_map.get(x[0], 999))

                ko_round_no = max_round
                ko_round_map = {}
                for rt, group_no, p1_id, p2_id in ko_placeholders:
                    if rt not in ko_round_map:
                        ko_round_no += 1
                        ko_round_map[rt] = ko_round_no
                    matches_to_insert.append(
                        dict(
                            event_id=event_id,
                            competition_type=comp,
                            group_no=group_no,
                            round_type=rt,
                            round_no=ko_round_map[rt],
                            player_1_id=p1_id,
                            player_1_club_id=None,
                            player_2_id=p2_id,
                            player_2_club_id=None,
                            status="pending",
                        )
                    )

                # === bulk insert =============================================
                with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
                    for row in matches_to_insert:
                        cur.execute(
                            """
                            insert into event_matches (
                                event_id, competition_type, group_no,
                                round_type, round_no,
                                player_1_id, player_1_club_id,
                                player_2_id, player_2_club_id,
                                status
                            )
                            values (%(event_id)s, %(competition_type)s, %(group_no)s,
                                    %(round_type)s, %(round_no)s,
                                    %(player_1_id)s, %(player_1_club_id)s,
                                    %(player_2_id)s, %(player_2_club_id)s,
                                    %(status)s)
                            """,
                            row,
                        )
                    conn.commit()

                st.success(f"✅ inserted {len(matches_to_insert)} matches.")
            except Exception as exc:
                st.error(f"❌ failed to insert matches: {exc}")

        # ---------------------------------------------------------------- scoring table
        edited_df = render_match_table(event_id, comp)
        if edited_df is not None:
            st.session_state["match_df"] = edited_df

        # ---------------------------------------------------------------- save scores
        if edited_df is not None and st.button("💾 save scores"):
            changed = edited_df.copy()
            orig = fetch_matches_df(event_id, comp)
            mask = (
                (changed["player1_goals"] != orig["player1_goals"])
                | (changed["player2_goals"] != orig["player2_goals"])
            )
            changed = changed[mask]
            if changed.empty:
                st.warning("no changes to save.")
            else:
                try:
                    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
                        for _, row in changed.iterrows():
                            if pd.isna(row["player1_goals"]) or pd.isna(row["player2_goals"]):
                                continue
                            cur.execute(
                                """
                                update event_matches
                                   set p1_goals = %s,
                                       p2_goals = %s,
                                       status = 'final',
                                       updated_timestamp = current_timestamp
                                 where id = %s
                                """,
                                (int(row["player1_goals"]), int(row["player2_goals"]), int(row["id"])),
                            )
                        conn.commit()
                    st.success("✅ scores saved; matches now 'final'.")
                    update_knockout_placeholders(event_id)
                    st.session_state["match_df"] = None
                    st.experimental_rerun()
                except Exception as exc:
                    st.error(f"❌ DB update failed: {exc}")

        # ---------------------------------------------------------------- simulate
        if edited_df is not None and st.button("🎲 simulate scores"):
            try:
                with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
                    cur.execute(
                        """
                        select id from event_matches
                        where event_id = %s and competition_type = %s and status = 'scheduled'
                        """,
                        (event_id, comp),
                    )
                    ids = [r[0] for r in cur.fetchall()]
                    for mid in ids:
                        p1, p2 = random.randint(0, 5), random.randint(0, 5)
                        cur.execute(
                            """
                            update event_matches
                               set p1_goals = %s, p2_goals = %s,
                                   status = 'final',
                                   updated_timestamp = current_timestamp
                             where id = %s
                            """,
                            (p1, p2, mid),
                        )
                    conn.commit()
                st.success(f"✅ simulated {len(ids)} matches.")
                update_knockout_placeholders(event_id)
                st.experimental_rerun()
            except Exception as exc:
                st.error(f"❌ simulation failed: {exc}")
