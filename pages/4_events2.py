import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from tabs import Details, Register, Tables, Scores, Result, Admin
from admin import new_event

st.set_page_config(page_title="Events", layout="wide")

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        np.random.randn(12, 5), columns=["a", "b", "c", "d", "e"]
    )

event = st.dataframe(
    st.session_state.df,
    key="data",
    on_select="rerun",
    selection_mode="single-row",
)

event.selection
