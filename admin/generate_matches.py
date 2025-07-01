import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import string
import random

def generate_knockout_placeholders(num_groups):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT ROUND_TYPE, GROUP_NO, P1_ID, P2_ID
            FROM KNOCKOUT_MATCHES
            WHERE %s BETWEEN MIN_GROUP AND MAX_GROUP
            ORDER BY ID
        """, (num_groups,))
        rows = cursor.fetchall()
        return [(row[0], row[1], row[2], row[3]) for row in rows]
    except Exception as e:
        st.error(f"Error loading knockout rules: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def update_knockout_placeholders(event_id):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE EVENT_MATCHES
            SET PLAYER_1_ID = ek.PLAYER_ID,
                PLAYER_1_CLUB_ID = ek.CLUB_ID,
                STATUS = case when PLAYER_2_ID > 0 then 'Scheduled' else STATUS end,
                UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
            FROM EVENT_KO_ROUND_V ek
            WHERE EVENT_MATCHES.EVENT_ID = %s
              AND EVENT_MATCHES.EVENT_ID = ek.EVENT_ID
              AND EVENT_MATCHES.STATUS <> 'Final'
              AND EVENT_MATCHES.COMPETITION_TYPE = ek.COMPETITION_TYPE
              AND EVENT_MATCHES.PLAYER_1_ID = ek.PLACEHOLDER_ID;
        """, (event_id,))

        cursor.execute("""
            UPDATE EVENT_MATCHES
            SET PLAYER_2_ID = ek.PLAYER_ID,
                PLAYER_2_CLUB_ID = ek.CLUB_ID,
                STATUS = case when PLAYER_1_ID > 0 then 'Scheduled' else STATUS end,
                UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
            FROM EVENT_KO_ROUND_V ek
            WHERE EVENT_MATCHES.EVENT_ID = %s
              AND EVENT_MATCHES.EVENT_ID = ek.EVENT_ID
              AND EVENT_MATCHES.STATUS <> 'Final'
              AND EVENT_MATCHES.COMPETITION_TYPE = ek.COMPETITION_TYPE
              AND EVENT_MATCHES.PLAYER_2_ID = ek.PLACEHOLDER_ID;
        """, (event_id,))

        conn.commit()
        st.success("✅ Knockout matches updated with actual player IDs and set to Scheduled")
        return True
    except Exception as e:
        st.error(f"❌ Failed to update knockout matches: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def render_match_table(event_id):
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
        cols = [desc[0].upper() for desc in cursor.description]
        df_matches = pd.DataFrame(matches, columns=cols)
    except Exception as e:
        st.error(f"❌ Failed to load matches: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

    if df_matches.empty:
        # st.info("ℹ️ No matches to show.")
        return None

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
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False,
        theme="alpine"
    )

    return pd.DataFrame(grid_response["data"])

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
            if st.button("🔁 Re-Generate Matches (This will delete all existing!)"):
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
                                    "STATUS": "Scheduled",
                                    "ROUND_TYPE": "Group"
                                })
                            rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

                    # Define desired knockout round order
                    max_round_no = round_no
                    knockout_order = [
                        "Barrage",
                        "Round of 64",
                        "Round of 32",
                        "Round of 16",
                        "Quarter-final",
                        "Semi-final",
                        "Final"
                    ]
                    round_order_map = {rt: i for i, rt in enumerate(knockout_order)}
                    
                    # ✅ Fetch placeholders FIRST
                    knockout_placeholders = generate_knockout_placeholders(len(comp_groups))
                    
                    # ✅ Sort based on round type importance
                    knockout_placeholders.sort(key=lambda x: round_order_map.get(x[0], 999))
                    
                    # Add knockout matches with consistent ROUND_NO assignment
                    ko_round_map = {}
                    ko_counter = max_round_no
                    for round_type, group_no, p1_id, p2_id in knockout_placeholders:
                        if round_type not in ko_round_map:
                            ko_counter += 1
                            ko_round_map[round_type] = str(ko_counter)
                        
                        match_rows.append({
                            "EVENT_ID": event_id,
                            "COMPETITION_TYPE": comp,
                            "GROUP_NO": group_no,
                            "ROUND_TYPE": round_type,
                            "ROUND_NO": ko_round_map[round_type],
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
                            EVENT_ID, COMPETITION_TYPE, GROUP_NO, ROUND_TYPE, ROUND_NO,
                            PLAYER_1_ID, PLAYER_1_CLUB_ID, PLAYER_2_ID, PLAYER_2_CLUB_ID,
                            STATUS
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row["EVENT_ID"], row["COMPETITION_TYPE"], row["GROUP_NO"], row["ROUND_TYPE"], row["ROUND_NO"],
                        row["PLAYER1_ID"], row["PLAYER1_CLUB_ID"],
                        row["PLAYER2_ID"], row["PLAYER2_CLUB_ID"],
                        row["STATUS"]
                    ))
                conn.commit()
                st.success(f"✅ {len(match_rows)} matches generated including knockouts.")
            except Exception as e:
                st.error(f"❌ Failed to generate matches: {e}")
            finally:
                cursor.close()
                conn.close()
        
        updated_df = render_match_table(event_id)
        if updated_df is not None:
            st.session_state["match_df"] = updated_df
                
        # Only allow saving if table loaded
        if updated_df is not None and st.button("💾 Save Scores"):    
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                for _, row in updated_df.iterrows():
                    if pd.isna(row["PLAYER1_GOALS"]) or pd.isna(row["PLAYER2_GOALS"]):
                        continue
                    cursor.execute("""
                        UPDATE EVENT_MATCHES
                        SET P1_GOALS = %s,
                            P2_GOALS = %s,
                            STATUS = 'Final',
                            UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                        WHERE ID = %s
                    """, (
                        int(row["PLAYER1_GOALS"]),
                        int(row["PLAYER2_GOALS"]),
                        int(row["ID"])
                    ))
                conn.commit()
                st.success("✅ Scores updated and matches marked as 'Final'.")
        
                # Automatically update placeholders
                update_knockout_placeholders(event_id)
        
                # Clear and rerun to reload match table cleanly
                st.session_state["match_df"] = None
                st.rerun()

            except Exception as e:
                st.error(f"❌ Failed to save scores: {e}")
            finally:
                cursor.close()
                conn.close()

        # Simulate scores for scheduled matches
        if updated_df is not None and st.button("🎲 Simulate Scores"):
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ID FROM EVENT_MATCHES
                    WHERE EVENT_ID = %s AND STATUS = 'Scheduled'
                """, (event_id,))
                match_ids = [row[0] for row in cursor.fetchall()]
        
                for match_id in match_ids:
                    p1_score = random.randint(0, 5)
                    p2_score = random.randint(0, 5)
                    cursor.execute("""
                        UPDATE EVENT_MATCHES
                        SET P1_GOALS = %s,
                            P2_GOALS = %s,
                            STATUS = 'Final',
                            UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
                        WHERE ID = %s
                    """, (p1_score, p2_score, match_id))
        
                conn.commit()
                st.success(f"✅ Simulated scores for {len(match_ids)} matches.")
                update_knockout_placeholders(event_id)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to simulate scores: {e}")
            finally:
                cursor.close()
                conn.close()
