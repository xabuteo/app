import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import string

def update_knockout_placeholders(event_id):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE EVENT_MATCHES
            SET PLAYER_1_ID = ek.PLAYER_ID,
                PLAYER_1_CLUB_ID = ek.CLUB_ID,
                STATUS = 'Scheduled',
                UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
            FROM EVENT_KO_ROUND_V ek
            WHERE EVENT_MATCHES.EVENT_ID = %s
              AND EVENT_MATCHES.EVENT_ID = ek.EVENT_ID
              AND EVENT_MATCHES.COMPETITION_TYPE = ek.COMPETITION_TYPE
              AND EVENT_MATCHES.PLAYER_1_ID = ek.PLACEHOLDER_ID;
        """, (event_id,))

        cursor.execute("""
            UPDATE EVENT_MATCHES
            SET PLAYER_2_ID = ek.PLAYER_ID,
                PLAYER_2_CLUB_ID = ek.CLUB_ID,
                STATUS = 'Scheduled',
                UPDATED_TIMESTAMP = CURRENT_TIMESTAMP
            FROM EVENT_KO_ROUND_V ek
            WHERE EVENT_MATCHES.EVENT_ID = %s
              AND EVENT_MATCHES.EVENT_ID = ek.EVENT_ID
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
        st.info("ℹ️ No matches to show.")
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
        theme="material"
    )

    return pd.DataFrame(grid_response["data"])

def render_match_generation(event_id):
    with st.expander("🎾 Match Generation & Scoring"):
        updated_df = render_match_table(event_id)

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

                updated_df = render_match_table(event_id)  # refresh grid only

            except Exception as e:
                st.error(f"❌ Failed to save scores: {e}")
            finally:
                cursor.close()
                conn.close()

        if st.button("🔁 Update Knockout Placeholders"):
            if update_knockout_placeholders(event_id):
                render_match_table(event_id)
