import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, get_userid

def page(selected_event):
    event_id = selected_event.get("ID")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *, case when round_type = 'Group' then 'Group '||GROUP_NO else ROUND_TYPE end as GROUP_LABEL
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
            # ➤ Group Matches
            groups = comp_df["GROUP_LABEL"].dropna().unique()
            groups.sort()

            for group in groups:
                group_df = comp_df[comp_df["GROUP_LABEL"] == group][[
                    "ROUND_NO", "PLAYER1", "PLAYER1_GOALS", "PLAYER2_GOALS", "PLAYER2", "STATUS"
                ]]

                def highlight_winner(row):
                    style = [''] * len(row)
                    p1_goals = row["PLAYER1_GOALS"]
                    p2_goals = row["PLAYER2_GOALS"]
                    if pd.notna(p1_goals) and pd.notna(p2_goals):
                        if p1_goals > p2_goals:
                            style[1] = 'background-color: lightcyan'
                        elif p2_goals > p1_goals:
                            style[4] = 'background-color: lightcyan'
                    return style

                styled_df = group_df.style.apply(highlight_winner, axis=1)
                st.markdown(f"#### {group}")
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # ➤ Knockout Matches (no group_no)
            knockout_df = comp_df[comp_df["GROUP_NO"].isna()].copy()

            if not knockout_df.empty:
                # Sort round order: R64 → R32 → R16 → QF → SF → F
                round_order = ["R64", "R32", "R16", "QF", "SF", "F"]
                knockout_df["ROUND_STAGE"] = knockout_df["ROUND_NO"].str.extract(r'([A-Z]+)')
                knockout_df["ROUND_INDEX"] = knockout_df["ROUND_STAGE"].apply(lambda x: round_order.index(x) if x in round_order else 99)
                knockout_df.sort_values(by=["ROUND_INDEX", "ROUND_NO"], inplace=True)

                for round_label in knockout_df["ROUND_STAGE"].dropna().unique():
                    round_matches = knockout_df[knockout_df["ROUND_STAGE"] == round_label][[
                        "ROUND_NO", "PLAYER1", "PLAYER1_GOALS", "PLAYER2_GOALS", "PLAYER2", "STATUS"
                    ]]

                    styled_knockout = round_matches.style.apply(highlight_winner, axis=1)
                    st.markdown(f"#### Knockout: {round_label}")
                    st.dataframe(styled_knockout, use_container_width=True, hide_index=True)
