import streamlit as st
import pandas as pd
from utils import get_snowflake_connection

def render_match_generation(event_id):
    st.header("🎾 Auto-Generate Matches")

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

    st.success("✅ Registrations loaded. Ready to generate matches.")

    if st.button("⚙️ Generate Round-Robin Matches"):
        try:
            match_rows = []
            for comp in df["COMPETITION_TYPE"].unique():
                for group in df[df["COMPETITION_TYPE"] == comp]["GROUP_NO"].unique():
                    group_df = df[(df["COMPETITION_TYPE"] == comp) & (df["GROUP_NO"] == group)]
                    players = group_df.to_dict("records")

                    # Add a BYE if odd number
                    if len(players) % 2 != 0:
                        players.append({
                            "ID": None,
                            "USER_ID": None,
                            "CLUB_ID": None,
                            "GROUP_NO": group,
                            "COMPETITION_TYPE": comp
                        })

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
                                "ROUND_NO": round_no,
                                "PLAYER1_ID": p1["USER_ID"],
                                "PLAYER1_CLUB_ID": p1["CLUB_ID"],
                                "PLAYER2_ID": p2["USER_ID"],
                                "PLAYER2_CLUB_ID": p2["CLUB_ID"],
                                "STATUS": "Scheduled"
                            })

                        # Rotate
                        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

            # Save matches
            conn = get_snowflake_connection()
            cursor = conn.cursor()

            for row in match_rows:
                cursor.execute("""
                    INSERT INTO EVENT_MATCHES (
                        EVENT_ID, COMPETITION_TYPE, GROUP_NO, ROUND_NO,
                        PLAYER1_ID, PLAYER1_CLUB_ID, PLAYER2_ID, PLAYER2_CLUB_ID,
                        STATUS, GENERATED_FLAG
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (
                    row["EVENT_ID"], row["COMPETITION_TYPE"], row["GROUP_NO"], row["ROUND_NO"],
                    row["PLAYER1_ID"], row["PLAYER1_CLUB_ID"],
                    row["PLAYER2_ID"], row["PLAYER2_CLUB_ID"],
                    row["STATUS"]
                ))
            conn.commit()
            st.success(f"✅ {len(match_rows)} matches generated and saved.")

        except Exception as e:
            st.error(f"❌ Failed to generate matches: {e}")
        finally:
            cursor.close()
            conn.close()

    # Display match view
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM EVENT_MATCHES_V
            WHERE event_id = %s
            ORDER BY COMPETITION_TYPE, GROUP_NO, ROUND_NO
        """, (event_id,))
        matches = cursor.fetchall()
        match_cols = [desc[0].upper() for desc in cursor.description]
        df_matches = pd.DataFrame(matches, columns=match_cols)
        st.markdown("### 📋 Matches")
        st.dataframe(df_matches, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Failed to load match view: {e}")
    finally:
        cursor.close()
        conn.close()
