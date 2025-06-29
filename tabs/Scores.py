import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, get_userid

def page(selected_event):
    event_id = selected_event.get("ID")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *, 
                case when round_type = 'Group' then 'Group '||GROUP_NO else ROUND_TYPE end as GROUP_LABEL,
                case when round_type = 'Group' then 1
                     when round_type = 'Barrage' then 2
                     when round_type = 'Round of 64' then 3
                     when round_type = 'Round of 32' then 4
                     when round_type = 'Round of 16' then 5
                     when round_type = 'Quarter-final' then 6
                     when round_type = 'Semi-final' then 7
                     when round_type = 'Final' then 8
                     else 99 end as sort_order
            FROM EVENT_MATCHES_V
            WHERE EVENT_ID = %s
            ORDER BY competition_type, sort_order, group_no, round_no
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
            # ➤ Group Matches
            groups = comp_df["GROUP_LABEL"].dropna().unique()
            # groups.sort()

            for group in groups:
                group_df = comp_df[comp_df["GROUP_LABEL"] == group][[
                    "ROUND_NO", "PLAYER1", "PLAYER1_GOALS", "PLAYER2_GOALS", "PLAYER2", "STATUS"
                ]]

                # Convert goal columns to Int64 for clean integer display
                group_df["PLAYER1_GOALS"] = group_df["PLAYER1_GOALS"].astype("Int64")
                group_df["PLAYER2_GOALS"] = group_df["PLAYER2_GOALS"].astype("Int64")
    
                def highlight_winner(row):
                    style = [''] * len(row)
                    p1_goals = row["PLAYER1_GOALS"]
                    p2_goals = row["PLAYER2_GOALS"]
                    if pd.notna(p1_goals) and pd.notna(p2_goals):
                        if p1_goals > p2_goals:
                            style[1] = 'background-color: #cce4ff'
                        elif p2_goals > p1_goals:
                            style[4] = 'background-color: #cce4ff'
                    return style

                styled_df = group_df.style.apply(highlight_winner, axis=1)
                st.markdown(f"#### {group}")
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
