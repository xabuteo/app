import streamlit as st
import pandas as pd
from utils import get_db_connection, get_userid

def page(selected_event):
    event_id = selected_event.get("ID")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM EVENT_TABLE_V
            WHERE EVENT_ID = %s
            AND ROUND_TYPE = 'Group'
            ORDER BY competition_type, group_no, rank
        """, (event_id,))
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"❌ Failed to load table data: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.info("ℹ️ No groups or matches have been assigned yet.")
        return

    competitions = sorted(df["COMPETITION_TYPE"].dropna().unique(), key=lambda x: (x != "Open", x))
    for comp in competitions:
        comp_df = df[df["COMPETITION_TYPE"] == comp]
        with st.expander(f"🏆 {comp} Competition", expanded=(comp == "Open")):
            groups = comp_df["GROUP_NO"].dropna().unique()
            groups.sort()
            for group in groups:
                group_df = comp_df[comp_df["GROUP_NO"] == group][[
                    "RANK", "PLAYER", "PLAYED", "WON", "DRAWN", "LOST", "GF", "GA", "GD", "PTS"
                ]]
                st.markdown(f"#### Group {group}")
                st.dataframe(group_df, use_container_width=True, hide_index=True)
