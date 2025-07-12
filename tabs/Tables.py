import streamlit as st
import pandas as pd
from utils import get_db_connection, get_userid

def page(selected_event):
    event_id = selected_event.get("id")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM event_table_v
            WHERE event_id = %s
            AND round_type = 'Group'
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

    competitions = sorted(df["competition_type"].dropna().unique(), key=lambda x: (x != "Open", x))
    for comp in competitions:
        comp_df = df[df["competition_type"] == comp]
        with st.expander(f"🏆 {comp} Competition", expanded=(comp == "Open")):
            groups = comp_df["group_no"].dropna().unique()
            groups.sort()
            for group in groups:
                group_df = comp_df[comp_df["group_no"] == group][[
                    "rank", "player", "played", "won", "drawn", "lost", "gf", "ga", "gd", "pts"
                ]]
                st.markdown(f"#### Group {group}")
                st.dataframe(group_df, use_container_width=True, hide_index=True)
