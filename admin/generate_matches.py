import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import string

def generate_knockout_placeholders(num_groups):
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT ROUND, ROUND_NO, P1_ID, P2_ID
            FROM KNOCKOUT_MATCHES
            WHERE %s BETWEEN MIN_GROUP AND MAX_GROUP
            ORDER BY ID
        """, (num_groups,))
        rows = cursor.fetchall()
        return [(row[0], row[1], row[2], row[3]) for row in rows]  # (round_label, round_no, p1_id, p2_id)
    except Exception as e:
        st.error(f"Error loading knockout rules: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def render_match_generation(event_id):
    with st.expander("🎾 Match Generation & Scoring"):
        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM EVENT_MATCHES WHERE event_id = %s", (event_id,))
            match_count = cursor.fetchone()[0]
        except Exception as e:
            st.error(f"❌ Could not check match state: {e}")
            return
        finally:
            cursor.close()
            conn.close()

        if match_count > 0:
            st.warning(f"⚠️ {match_count} matches already exist. Re-generating will **DELETE all matches and scores**.")
            if not st.button("🔁 Re-Generate Matches (This will delete all existing!)"):
                st.info("⚠️ Skipped regeneration. Existing matches below:")
            else:
                try:
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM EVENT_MATCHES WHERE event_id = %s", (event_id,))
                    conn.commit()
                    st.success("✅ Old matches deleted. You can now generate new ones.")
                    match_count = 0
                except Exception as e:
                    st.error(f"❌ Failed to delete old matches: {e}")
                    return
                finally:
                    cursor.close()
                    conn.close()

        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, club_id, group_no, competition_type
                FROM event_registration
                WHERE event_id = %s AND group_no IS NOT NULL
            """, (event_id,))
            rows = cursor.fetchall()
            cols = [desc[0].upper() for desc in cursor.description]
            df = pd.DataFrame(rows, columns=cols)
        except Exception as e:
            st.error(f"❌ Failed to load registration data: {e}")
            return
        finally:
            cursor.close()
            conn.close()

        if df.empty:
            st.info("ℹ️ No groupings found for this event.")
            return

        if match_count == 0 and st.button("⚙️ Generate Round-Robin Matches"):
            try:
                match_rows = []
                group_letters = {}
                letter_iter = iter(string.ascii_uppercase)

                for comp in df["COMPETITION_TYPE"].unique():
                    comp_df = df[df["COMPETITION_TYPE"] == comp]
                    comp_groups = sorted(comp_df["GROUP_NO"].unique())
                    group_map = {group: next(letter_iter) for group in comp_groups}
                    group_letters[comp] = group_map

                    for group in comp_groups:
                        group_df = comp_df[comp_df["GROUP_NO"] == group]
                        players = group_df.to_dict("records")

                        if len(players) % 2 != 0:
                            players.append({"ID": None, "USER_ID": -1, "CLUB_ID": None, "GROUP_NO": group, "COMPETITION_TYPE": comp})

                        n = len(players)
                        rounds = n - 1
                        half = n // 2
                        rotation = players[:]

                        for round_no in range(1, rounds + 1):
                            for i in range(half):
                                p1 = rotation[i]
                                p2 = rotation[n - 1 - i]
                                match_rows.append({
                                    "EVENT_ID": event_id,
                                    "COMPETITION_TYPE": comp,
                                    "GROUP_NO": group,
                                    "ROUND_NO": str(round_no),
                                    "PLAYER1_ID": p1["USER_ID"],
                                    "PLAYER1_CLUB_ID": p1["CLUB_ID"],
                                    "PLAYER2_ID": p2["USER_ID"],
                                    "PLAYER2_CLUB_ID": p2["CLUB_ID"],
                                    "STATUS": "Scheduled"
                                })
                            rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

                    # Add knockout placeholder matches
                    knockout_placeholders = generate_knockout_placeholders(len(comp_groups))
                    for round_label, round_no, p1_id, p2_id in knockout_placeholders:
                        match_rows.append({
                            "EVENT_ID": event_id,
                            "COMPETITION_TYPE": comp,
                            "GROUP_NO": round_label,  # store ROUND into GROUP_NO
                            "ROUND_NO": round_no,
                            "PLAYER1_ID": p1_id,
                            "PLAYER1_CLUB_ID": None,
                            "PLAYER2_ID": p2_id,
                            "PLAYER2_CLUB_ID": None,
                            "STATUS": "Pending"
                        })

                conn = get_snowflake_connection()
                cursor = conn.cursor()
                for row in match_rows:
                    cursor.execute("""
                        INSERT INTO EVENT_MATCHES (
                            EVENT_ID, COMPETITION_TYPE, GROUP_NO, ROUND_NO,
                            PLAYER_1_ID, PLAYER_1_CLUB_ID, PLAYER_2_ID, PLAYER_2_CLUB_ID,
                            STATUS
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row["EVENT_ID"], row["COMPETITION_TYPE"], row["GROUP_NO"], row["ROUND_NO"],
                        row.get("PLAYER1_ID"), row.get("PLAYER1_CLUB_ID"),
                        row.get("PLAYER2_ID"), row.get("PLAYER2_CLUB_ID"),
                        row["STATUS"]
                    ))
                conn.commit()
                st.success(f"✅ {len(match_rows)} matches generated including knockouts.")
            except Exception as e:
                st.error(f"❌ Failed to generate matches: {e}")
            finally:
                cursor.close()
                conn.close()

        # Remaining logic unchanged (group completion check, display and update match scores)...
