from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import pandas as pd
import streamlit as st

# Dummy data for testing
data = {
    "ID": [1, 2, 3],
    "EVENT_TITLE": ["Chess Open", "Junior Cup", "Veteran League"],
    "EVENT_TYPE": ["Open", "Junior", "Veteran"],
    "EVENT_START_DATE": ["2025-06-01", "2025-06-15", "2025-07-01"],
    "EVENT_END_DATE": ["2025-06-05", "2025-06-18", "2025-07-04"],
    "EVENT_STATUS": ["Planned", "Approved", "Closed"],
    "EVENT_OPEN": [True, False, False],
    "EVENT_WOMEN": [True, True, False],
    "EVENT_JUNIOR": [False, True, False],
    "EVENT_VETERAN": [False, False, True],
    "EVENT_TEAMS": [True, False, True],
    "REG_OPEN_DATE": ["2025-05-01", "2025-05-10", "2025-05-20"],
    "REG_CLOSE_DATE": ["2025-05-30", "2025-06-10", "2025-06-25"],
    "EVENT_LOCATION": ["Sydney", "Melbourne", "Brisbane"],
    "EVENT_EMAIL": ["chess@example.com", "junior@example.com", "veteran@example.com"],
    "EVENT_COMMENTS": ["Open to all", "Under 18 only", "Over 50 only"]
}
df = pd.DataFrame(data)

st.set_page_config(layout="wide")
st.title("📅 Events")

# Format date columns
for col in ["EVENT_START_DATE", "EVENT_END_DATE", "REG_OPEN_DATE", "REG_CLOSE_DATE"]:
    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')

# Configure AgGrid
gb = GridOptionsBuilder.from_dataframe(df[[
    "ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_START_DATE", "EVENT_END_DATE", "EVENT_STATUS"
]])
gb.configure_selection(selection_mode="single", use_checkbox=True)
grid_options = gb.build()

grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    theme="streamlit",
    height=400
)

# Extract selected row
selected = grid_response.get("selected_rows", [])
if selected:
    selected_id = selected[0]["ID"]
    selected_row = df[df["ID"] == selected_id].iloc[0]

    with st.container():
        st.subheader(f"📄 Event Details: {selected_row['EVENT_TITLE']}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Type:** {selected_row['EVENT_TYPE']}")
            st.markdown(f"**Start Date:** {selected_row['EVENT_START_DATE']}")
            st.markdown(f"**End Date:** {selected_row['EVENT_END_DATE']}")
            st.markdown(f"**Registration Open:** {selected_row['REG_OPEN_DATE']}")
            st.markdown(f"**Registration Close:** {selected_row['REG_CLOSE_DATE']}")
            st.markdown(f"**Location:** {selected_row['EVENT_LOCATION']}")
            st.markdown(f"**Email:** {selected_row['EVENT_EMAIL']}")
        with col2:
            st.markdown(f"**Status:** {selected_row['EVENT_STATUS']}")
            st.markdown("**Categories:**")
            st.markdown(f"- Open: {'✅' if selected_row['EVENT_OPEN'] else '❌'}")
            st.markdown(f"- Women: {'✅' if selected_row['EVENT_WOMEN'] else '❌'}")
            st.markdown(f"- Junior: {'✅' if selected_row['EVENT_JUNIOR'] else '❌'}")
            st.markdown(f"- Veteran: {'✅' if selected_row['EVENT_VETERAN'] else '❌'}")
            st.markdown(f"- Teams: {'✅' if selected_row['EVENT_TEAMS'] else '❌'}")

        st.markdown("**Comments:**")
        st.info(selected_row["EVENT_COMMENTS"] or "No comments")

        st.markdown("#### Actions")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.button("✅ Approve")
        with col2: st.button("📝 Register")
        with col3: st.button("🛑 Close")
        with col4: st.button("📦 Complete")
