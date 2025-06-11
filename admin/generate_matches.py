import streamlit as st
import pandas as pd
from utils import get_snowflake_connection

def generate_round_robin(players):
    """Generate round-robin schedule with BYE support."""
    if len(players) % 2:
        players.append({"USER_ID": -1, "CLUB_ID": None})  # BYE represented by -1

    num_players = len(players)
    rounds = []

    for round_idx in range(num_players - 1):
        matches = []
        for i in range(num_players // 2):
            p1 = players[i]
            p2 = players[num_players - 1 - i]
            if p1["USER_ID"] != -1 and p2["USER_ID"] != -1:
                matches.append((p1, p2))
            elif p1["USER_ID"] != -1:
                matches.append((p1, {"USER_ID": -1, "CLUB_ID": None}))
            elif p2["USER_ID"] != -1:
                matches.append((p2, {"USER_ID": -1, "CLUB_ID": None}))
        rounds.append(matches)
        players = [players[0]] + [players[-1]] + players[1:-1]
    return rounds

def render(event_id):
    with st.expander("🎮 Generate Matches"):
        st.markdown("This will generate round-robin matches for each group and competition.")

        if st.button("🔄 Generate Round-Robin Matches"):
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT user_id, club_id, competition_type, group_no
                    FROM event_registration
                    WHERE event_id = %s AND group_no IS NOT NULL
                    ORDER BY competition_type, group_no
                """, (event_id,))
                rows = cursor.fetchall()
                if not rows:
                    st.warning("No players with groups found.")
                    return

                df = pd.DataFrame(rows, columns=["USER_ID", "CLUB_ID", "COMPETITION_TYPE", "GROUP_NO"])
                all_matches = []

                for (comp, group), group_df in df.groupby(["COMPETITION_TYPE", "GROUP_NO"]):
                    players = group_df[["USER_ID", "CLUB_ID"]].to_dict(orient="records")
                    rounds = generate_round_robin(players)

                    for round_no, match_round in enumerate(rounds, 1):
                        for p1, p2 in match_round:
                            all_matches.append({
                                "event_id": event_id,
                                "competition_type": comp,
                                "group_no": group,
                                "round_no": round_no,
                                "player_1_id": int(p1["USER_ID"]),
                                "player_1_club_id": p1["CLUB_ID"],
                                "player_2_id": int(p2["USER_ID"]),
                                "player_2_club_id": p2["CLUB_ID"]
                            })

                match_df = pd.DataFrame(all_matches)

                for _, row in match_df.iterrows():
                for _, row in matches_df.iterrows():
                    row = {k: (None if pd.isna(v) else v) for k, v in row.items()}  # Clean NaNs
                
                    cursor.execute("""
                        INSERT INTO event_matches (
                            event_id, competition_type, group_no, round_no,
                            player_1_id, player_1_club_id, player_2_id, player_2_club_id,
                            status, updated_timestamp
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Scheduled', CURRENT_TIMESTAMP)
                    """, (
                        row["event_id"], row["competition_type"], row["group_no"], row["round_no"],
                        row["player_1_id"], row["player_1_club_id"],
                        row["player_2_id"], row["player_2_club_id"]
                    ))

                conn.commit()
                st.success(f"✅ {len(match_df)} matches generated and saved.")
                st.dataframe(match_df)

            except Exception as e:
                st.error(f"❌ Failed to generate matches: {e}")
            finally:
                cursor.close()
                conn.close()
