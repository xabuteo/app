import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import random

# Sample color list
colors = ["Red", "Green", "Blue", "Orange", "Purple"]

# Generate mock data
data = [{"color": random.choice(colors), "value": random.randint(0, 1000)} for _ in range(20)]
df = pd.DataFrame(data)

st.title("🎨 Editable AgGrid Table")

# Format value as currency (e.g. £ 123)
value_formatter = JsCode("""
function(params) {
    return "£ " + params.value;
}
""")

# Cell editor validator for max length (text)
max_length_validator = JsCode("""
function(params) {
    if (params.newValue.length > 20) {
        return false;
    }
    return true;
}
""")

# Setup Grid Options
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(editable=True, resizable=True)
gb.configure_column("color", 
                    editable=True, 
                    cellEditor="agTextCellEditor",
                    onCellValueChanged=max_length_validator)
gb.configure_column("value", 
                    editable=True,
                    type=["numericColumn"],
                    valueFormatter=value_formatter,
                    cellEditor="agTextCellEditor")

# Final grid
grid_options = gb.build()

grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    height=500,
    width='100%',
    allow_unsafe_jscode=True,  # Required for JsCode to work
    update_mode=GridUpdateMode.VALUE_CHANGED,
    enable_enterprise_modules=False,
    theme="streamlit",  # or "balham", "material"
)

# Show updated data
updated_df = grid_response["data"]
st.subheader("📦 Updated DataFrame")
st.dataframe(updated_df)
