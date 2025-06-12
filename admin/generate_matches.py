import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def render_match_generation(event_id):
    st.expander("🎾 Match Generation & Scoring")

    # Check if matches already exist
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
                cursor.close()
                conn.close()
                st.success("✅ Old matches deleted. You can now generate new ones.")
                match_count = 0  # Reset
            except Exception as e:
                st.error(f"❌ Failed to delete old matches: {e}")
                return

    # Load group registration
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
            for comp in df["COMPETITION_TYPE"].unique():
                for group in df[df["COMPETITION_TYPE"] == comp]["GROUP_NO"].unique():
                    group_df = df[(df["COMPETITION_TYPE"] == comp) & (df["GROUP_NO"] == group)]
                    players = group_df.to_dict("records")

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
                        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

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
            st.success(f"✅ {len(match_rows)} matches generated.")
        except Exception as e:
            st.error(f"❌ Failed to generate matches: {e}")
        finally:
            cursor.close()
            conn.close()

    # View & Edit Matches
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, competition_type, round_no, group_no,
                   player1, player1_goals, player2_goals, player2
            FROM EVENT_MATCHES_V
            WHERE event_id = %s
            ORDER BY round_no, group_no
        """, (event_id,))
        matches = cursor.fetchall()
        match_cols = [desc[0].upper() for desc in cursor.description]
        df_matches = pd.DataFrame(matches, columns=match_cols)
    except Exception as e:
        st.error(f"❌ Failed to load matches: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    st.markdown("### 📋 Match Results")
    gb = GridOptionsBuilder.from_dataframe(df_matches)
    gb.configure_default_column(editable=False)
    gb.configure_column("PLAYER1_GOALS", editable=True)
    gb.configure_column("PLAYER2_GOALS", editable=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df_matches,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        fit_columns_on_grid_load=True,
        theme="material"
    )

    updated_df = pd.DataFrame(grid_response["data"])
    if st.button("💾 Save Scores"):
        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            for _, row in updated_df.iterrows():
                cursor.execute("""
                    UPDATE EVENT_MATCHES
                    SET P1_GOALS = %s,
                        P2_GOALS = %s,
                        STATUS = 'Final',
                        UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                    WHERE ID = %s
                """, (
                    row["PLAYER1_GOALS"],
                    row["PLAYER2_GOALS"],
                    row["ID"]
                ))
            conn.commit()
            st.success("✅ Scores updated and matches marked as 'Final'.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to save scores: {e}")
        finally:
            cursor.close()
            conn.close()
