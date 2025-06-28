# xabuteo.py

import streamlit as st
from utils import get_snowflake_connection, ensure_profile_complete

st.set_page_config(
    page_title="Xabuteo",
    page_icon="☝️",
    initial_sidebar_state="auto",
    layout="centered",
)

import pandas as pd
import datetime

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
        (1, "Access app", "Go to https://xabuteo.streamlit.app/", "If the app hasn't been accessed for a while, you might need to \"wake it up\""),
        (2, "Sign-up", "Click on login/sign-up button", ""),
        (3, "Sign-up", "Click on sign-up link, enter email and password and click contiunue", "Currently, logins in all users immediately. Can change this behaviour to require email confirmation and/or approval"),
        (4, "Update profile", "Click on Profile in Menu", ""),
        (5, "Update profile", "Click on \"Update Profile\", update first name, last name, DOB and gender and click Update", "More details can be captured in profile"),
        (6, "Add club", "Click on Club in menu", "Will require profile update before displaying."),
        (7, "Add club", "Click on \"Request New Club\"", ""),
        (8, "Add club", "Select ATFA and Canberra, change dates and click Submit", "Rules about when/what clubs can be selected can be applied"),
        (9, "Approve club", "Click on Admin Club Requests in menu", "This is open just for testing but normally restricted to club admins"),
        (10, "Approve club", "Click on Approve", ""),
        (11, "Approve club", "Check club request by clicking on Club", "Status will be approved"),
        (12, "Create event", "Click on Events in the Menu", ""),
        (13, "Create event", "Click on event TEST1 then Admin", "This is a work around for testing. Event creation will be limited to Event admins"),
        (14, "Create event", "Click on Add New Event", ""),
        (15, "Create event", "Enter details with Start date in the future and Registration starting before and ending after today", ""),
        (16, "Create event", "Click Add Event", ""),
        (17, "View event", "Click on Events in the Menu or Back to Event List", ""),
        (18, "View event", "Search for event using the filters", ""),
        (19, "View event", "Select event", ""),
        (20, "View event", "Select Register", "You won't be able to register as the status is pending"),
        (21, "Approve event", "Click on Admin", ""),
        (22, "Approve event", "Click on Approve", ""),
        (23, "Register for event", "Select Register", ""),
        (24, "Register for event", "Select competitions and click Register", ""),
        (25, "Register for event", "Click on View Registered Competitors", ""),
        (26, "Register for event", "Click on button to Load Test Competitors", ""),
        (27, "Setup event", "Click on Admin", ""),
        (28, "Setup event", "Select competion and update a couple of seeds", ""),
        (29, "Setup event", "Click Save Seeding", ""),
        (30, "Setup event", "Click on Auto-Grouping", ""),
        (31, "Setup event", "Select the competition and number of groups (2 or 3)", ""),
        (32, "Setup event", "Click Auto Assign", ""),
        (33, "Setup event", "Check groups and click Save Assigned Groups", ""),
        (34, "Setup event", "Click on Match Regeration and click Generate Round-Robin", ""),
        (35, "Setup event", "Click on Table tab to check tables (end user view)", ""),
        (36, "Setup event", "Click on Scores tab to view matches (end user view)", ""),
        (37, "Run event", "Either enter and save scores or click simulate scores", "Simulate only used for testing"),
        (38, "Run event", "Click on Table tab to check tables (end user view)", ""),
        (39, "Run event", "Click on Scores tab to view matches (end user view)", ""),
        (40, "Run event", "Click on Admin and Match Generation", ""),
        (41, "Run event", "Click on simulate scores for each knockout round", ""),
        (42, "Run event", "Click on admin tab and 'Complete' button", ""),
        (43, "Run event", "Click on Result tab to view final results", ""),
        (44, "Logout", "Click on logout in menu", "")
    ]
    
    df = pd.DataFrame(data, columns=["Step No", "Group", "Step", "Notes"])
    df = df.sort_values("Step No")  # Ensure steps are ordered

    grouped = df.groupby("Group", sort=False)  # Maintain first occurrence order of groups

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
