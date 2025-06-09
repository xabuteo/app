import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, get_userid

def page(selected_event):
    event_status = selected_event.get("EVENT_STATUS", "")
    event_id = selected_event.get("ID")
    user_id = get_userid()

    with st.expander(f"🏓 Tables", expanded=True):
        try:
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM EVENT_TABLE_V
                WHERE EVENT_ID = %s
                ORDER BY competition_type, last_name, first_name
            """, (event_id,))
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=cols)
        except Exception as e:
            st.error(f"❌ Failed to load registrations: {e}")
            return
        finally:
            cursor.close()
            conn.close()
    
        if df.empty:
            st.info("No groups assigned yet.")
        else:
            competitions = df["COMPETITION_TYPE"].unique()
            for comp in competitions:
                comp_df = df[df["COMPETITION_TYPE"] == comp][["FIRST_NAME", "LAST_NAME", "CLUB_CODE", "PLAYED", "WON", "DRAWN", "LOST", "GF", "GA", "GD", "PTS"]]
                st.markdown(f"### 🏆 {comp} Competition")
                st.dataframe(comp_df, use_container_width=True)
