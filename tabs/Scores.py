import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, get_userid

def page(selected_event):
    event_id = selected_event.get("ID")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM EVENT_MATCHES_V
            WHERE EVENT_ID = %s
            ORDER BY competition_type, group_no, round_no
        """, (event_id,))
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"❌ Failed to load matches: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.info("ℹ️ No matches have been assigned yet.")
        return

    competitions = sorted(df["COMPETITION_TYPE"].dropna().unique(), key=lambda x: (x != "Open", x))
    for comp in competitions:
        comp_df = df[df["COMPETITION_TYPE"] == comp]
        with st.expander(f"🏆 {comp} Competition", expanded=(comp == "Open")):
            groups = comp_df["GROUP_NO"].dropna().unique()
            groups.sort()
            for group in groups:
                group_df = comp_df[comp_df["GROUP_NO"] == group][[
                    "ROUND_NO", "PLAYER1", "PLAYER1_GOALS", "PLAYER2_GOALS", "PLAYER2", "STATUS"
                ]]

                # Highlight the winner's player cell with light cyan
                def highlight_winner(row):
                    style = [''] * len(row)
                    if row["PLAYER1_GOALS"] > row["PLAYER2_GOALS"]:
                        style[1] = 'background-color: lightcyan'
                    elif row["PLAYER2_GOALS"] > row["PLAYER1_GOALS"]:
                        style[4] = 'background-color: lightcyan'
                    return style

                styled_df = group_df.style.apply(highlight_winner, axis=1)

                st.markdown(f"#### Group {group}")
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
