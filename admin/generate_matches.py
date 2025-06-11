import streamlit as st
import pandas as pd
from itertools import combinations
from utils import get_snowflake_connection

def generate_matches(event_id, competition):
    with st.expander("🎮 Generate Matches"):
        if st.button("🔁 Generate Round-Robin Matches"):
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                
                # Load players for selected event and competition
                cursor.execute("""
                    SELECT user_id, club_id, group_no
                    FROM EVENT_REGISTRATION
                    WHERE event_id = %s
                      AND competition_type = %s
                      AND group_no IS NOT NULL
                    ORDER BY group_no
                """, (event_id, competition))
                rows = cursor.fetchall()
                if not rows:
                    st.warning("No registered players with group assignments.")
                    return
                
                df = pd.DataFrame(rows, columns=["player_id", "club_id", "group_no"])
                
                # Generate round-robin matches
                all_matches = []
                for group in df["group_no"].unique():
                    group_players = df[df["group_no"] == group].reset_index(drop=True)
                    players = list(group_players.itertuples(index=False))

                    if len(players) % 2 != 0:
                        players.append(("BYE", None, group))  # pad with BYE

                    num_rounds = len(players) - 1
                    num_matches_per_round = len(players) // 2

                    schedule = []
                    for rnd in range(num_rounds):
                        round_matches = []
                        for i in range(num_matches_per_round):
                            p1 = players[i]
                            p2 = players[-(i+1)]
                            round_matches.append((p1, p2))
                        players = [players[0]] + [players[-1]] + players[1:-1]
                        schedule.append(round_matches)

                    for rnd, round_matches in enumerate(schedule, start=1):
                        for p1, p2 in round_matches:
                            is_bye = "BYE" in [p1[0], p2[0]]
                            match = {
                                "event_id": event_id,
                                "competition_type": competition,
                                "group_no": group,
                                "round_no": rnd,
                                "player_1_id": None if p1[0] == "BYE" else p1[0],
                                "player_1_club_id": None if p1[0] == "BYE" else p1[1],
                                "player_2_id": None if p2[0] == "BYE" else p2[0],
                                "player_2_club_id": None if p2[0] == "BYE" else p2[1],
                                "is_bye": is_bye
                            }
                            all_matches.append(match)

                # Insert into DB
                for match in all_matches:
                    cursor.execute("""
                        INSERT INTO EVENT_MATCHES (
                            event_id, competition_type, group_no, round_no,
                            player_1_id, player_1_club_id,
                            player_2_id, player_2_club_id,
                            is_bye, status, updated_timestamp
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Scheduled', CURRENT_TIMESTAMP)
                    """, (
                        match["event_id"], match["competition_type"], match["group_no"], match["round_no"],
                        match["player_1_id"], match["player_1_club_id"],
                        match["player_2_id"], match["player_2_club_id"],
                        match["is_bye"]
                    ))

                conn.commit()
                st.success(f"✅ {len(all_matches)} matches generated and saved.")

                # Display generated matches from view
                cursor.execute("""
                    SELECT *
                    FROM EVENT_MATCHES_V
                    WHERE event_id = %s AND competition_type = %s
                    ORDER BY group_no, round_no
                """, (event_id, competition))
                matches_view = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                view_df = pd.DataFrame(matches_view, columns=cols)
                st.dataframe(view_df, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Failed to generate matches: {e}")
            finally:
                cursor.close()
                conn.close()
