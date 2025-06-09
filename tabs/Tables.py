import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, get_userid

def page(selected_event):
    event_status = selected_event.get("EVENT_STATUS", "")
    event_id = selected_event.get("ID")
    user_id = get_userid()

    with st.container(border=True):
        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM EVENT_TABLE_V
                WHERE EVENT_ID = %s
                ORDER BY competition_type, group_no, last_name, first_name
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
                        "FIRST_NAME", "LAST_NAME", "CLUB_CODE", "PLAYED", "WON", "DRAWN", "LOST", "GF", "GA", "GD", "PTS"
                    ]]
                    st.markdown(f"#### Group {group}")
                    st.dataframe(group_df, use_container_width=True)
