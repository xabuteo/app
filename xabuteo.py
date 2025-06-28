# xabuteo.py

import streamlit as st
from utils import get_snowflake_connection, ensure_profile_complete

st.set_page_config(
    page_title="Xabuteo",
    page_icon="☝️",
    initial_sidebar_state="auto",
    layout="centered",
)

import streamlit as st
import pandas as pd
import datetime
from utils import get_snowflake_connection

# ---------- BUG LOGGING ----------
with st.sidebar.expander("🐞 Report a Bug"):
    st.markdown("Use the form below to log a bug.")
    with st.form("bug_form"):
        bug_summary = st.text_input("Summary", max_chars=100)
        bug_description = st.text_area("Description")
        page = st.text_input("Page / Feature (optional)")
        severity = st.selectbox("Severity", ["Low", "Medium", "High", "Critical"])
        submitted = st.form_submit_button("Submit Bug")

        if submitted:
            try:
                conn = get_snowflake_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO APP_BUGS (SUMMARY, DESCRIPTION, PAGE, SEVERITY, REPORTED_AT)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (bug_summary, bug_description, page, severity))
                conn.commit()
                st.success("✅ Bug logged successfully.")
            except Exception as e:
                st.error(f"❌ Failed to submit bug: {e}")
            finally:
                cursor.close()
                conn.close()


# ---------- TESTING CHECKLIST ----------
with st.sidebar.expander("🧪 Testing Checklist"):
    # Replace this with your actual table if dynamically loading from DB or CSV
    data = [
        (1, "Access app", "https://xabuteo.streamlit.app/", "If the app hasn't been accessed for a while, you might need to 'wake it up'"),
        (2, "Sign-up", "Click on login/sign-up button", ""),
        (3, "Sign-up", "Click on sign-up link, enter email and password and click continue", "Currently, logins in all users immediately. Can change this behaviour..."),
        # Add all remaining steps here...
    ]

    df = pd.DataFrame(data, columns=["Step No", "Group", "Step", "Notes"])
    grouped = df.groupby("Group")

    for group, steps in grouped:
        st.markdown(f"**{group}**")
        for _, row in steps.iterrows():
            st.checkbox(
                label=row["Step"],
                key=f"step_{int(row['Step No'])}",
                help=row["Notes"] if row["Notes"] else None
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
