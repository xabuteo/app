import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from tabs import Details, Register, Tables, Scores, Result, Admin
from admin import new_event

st.set_page_config(page_title="Events", layout="wide")
st.title("📅 Events")

# Load events
try:
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events_v ORDER BY EVENT_START_DATE DESC")
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    st.session_state.df = pd.DataFrame(rows, columns=cols)
except Exception as e:
    st.error(f"Error loading events: {e}")
finally:
    cursor.close()
    conn.close()

if st.session_state.df.empty:
        st.info("No events found.")
        new_event.add_new_event()

event = st.dataframe(
    st.session_state.df,
    key="data",
    on_select="rerun",
    selection_mode="single-row",
)

event.selection
