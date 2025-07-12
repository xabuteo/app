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
            FROM event_result_v
            WHERE event_id = %s
            ORDER BY event_id, competition_type, round_no DESC, final
        """, (event_id,))
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"❌ Failed to load final result: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.info("ℹ️ Result has not been finalised.")
        return

    competitions = sorted(df["competition_type"].dropna().unique(), key=lambda x: (x != "Open", x))

    for comp in competitions:
        comp_df = df[df["competition_type"] == comp][["player", "final_result"]]
        with st.expander(f"🏆 {comp} Competition", expanded=(comp == "Open")):

            def highlight_winner(row):
                style = [''] * len(row)
                if row["final_result"] == "Winner":
                    style[1] = 'background-color: #cce4ff'
                return style

            styled_df = comp_df.style.apply(highlight_winner, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
