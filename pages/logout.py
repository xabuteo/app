import streamlit as st

st.set_page_config(page_title="Logout", layout="wide")

def show():
    st.title("🚪 Logout")

    if "user_email" in st.session_state:
        user_name = st.session_state.get("user_name", st.session_state["user_email"])
        st.success(f"👋 Goodbye, {user_name}!")

        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.info("🔐 You have been logged out.")
        st.markdown("[🔙 Return to Home](/)")
    else:
        st.info("🔐 You are not logged in.")
