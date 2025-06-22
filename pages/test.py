import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

# Sample data
df = pd.DataFrame({
    "Name": ["Alice", "Bob", "Charlie"],
    "Score": [85, 92, 78],
    "Passed": [True, True, False]
})

# Theme options
themes = [
    "streamlit",     # default
    "material",
    "balham",
    "balham-dark",
    "alpine",
    "alpine-dark"
]

# UI - theme selector
st.title("🎨 AgGrid Theme Showcase")
selected_theme = st.selectbox("Choose a theme", themes)

# Grid configuration
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_selection("single", use_checkbox=True)
grid_options = gb.build()

# Display the table
st.subheader(f"Theme: `{selected_theme}`")
AgGrid(
    df,
    gridOptions=grid_options,
    theme=selected_theme,
    fit_columns_on_grid_load=True,
    height=250
)
