# xabuteo.py

import streamlit as st
from utils import get_snowflake_connection, ensure_profile_complete

query_params = st.query_params()

# Set test mode in session state based on URL param
if "test" in query_params and query_params["test"][0] == "1":
    st.session_state["test_mode"] = True
else:
    st.session_state["test_mode"] = False

st.set_page_config(
    page_title="Xabuteo",
    page_icon="☝️",
    initial_sidebar_state="auto",
    layout="centered",
)
            
# Page content
st.title("Xabuteo")

if not st.user.is_logged_in:
    # Not yet logged in: show login link and stop
    if st.button(
        "✨ Login or Sign up to the Xabuteo site",
        type="primary",
        key="checkout-button",
        use_container_width=True,
    ):
        st.login("auth0")
else:
    email = getattr(st.user, "email", None)
    auth_id = getattr(st.user, "sub", None)
    
    # Try to get first_name and family_name from user attributes
    first_name = getattr(st.user, "given_name", None)
    last_name = getattr(st.user, "family_name", None)
    
    # Fallback if not available (email/password users)
    if not first_name and hasattr(st.user, "name"):
        first_name = st.user.name
    if not last_name:
        last_name = ""

    # Insert into Snowflake (if new)
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            MERGE INTO registrations AS tgt
            USING (
                SELECT 
                    %s AS email,
                    %s AS auth0_id,
                    %s AS first_name,
                    %s AS last_name,
                    CURRENT_TIMESTAMP() AS date_registered,
                    CURRENT_TIMESTAMP() AS updated_at,
                    %s AS updated_by
            ) AS src
            ON tgt.email = src.email
            WHEN NOT MATCHED THEN
                INSERT (email, auth0_id, first_name, last_name, date_registered, updated_at, updated_by)
                VALUES (src.email, src.auth0_id, src.first_name, src.last_name, src.date_registered, src.updated_at, src.updated_by)
            """,
            (email, auth_id, first_name, last_name, email),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


    st.success(f"Welcome, {st.user.email}!")
    st.json(st.user.to_dict())

    if st.button(
        "✨ Log out",
        type="primary",
        key="checkout-button",
        use_container_width=True,
    ):
        st.logout()

from sidebar_utils import render_sidebar_widgets
st.write("Test Mode:", st.session_state.get("test_mode", False))
render_sidebar_widgets()
