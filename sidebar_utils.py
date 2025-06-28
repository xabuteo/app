import streamlit as st
import pandas as pd

@st.cache_resource
def get_persistent_step_state():
    return {}

def render_sidebar_widgets():
    persistent_state = get_persistent_step_state()

    # Testing Checklist
    with st.sidebar.expander("🧪 Testing Checklist"):
        data = [
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
            (14, "Create event", "Click on Add New Event", "Event creation will be limited to Event admins"),
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
        df = pd.DataFrame(data, columns=["Step No", "Group", "Step", "Notes"]).sort_values("Step No")
        grouped = df.groupby("Group", sort=False)

        for group, steps in grouped:
            st.markdown(f"**{group}**")
            for _, row in steps.iterrows():
                key = f"step_{int(row['Step No'])}"
                if key not in st.session_state:
                    st.session_state[key] = False
        
                st.checkbox(
                    label=row["Step"],
                    value=st.session_state[key],
                    key=key,
                    help=row["Notes"] if row["Notes"] else None
                )

                
    # Bug Report
    with st.sidebar.expander("🐞 Report a Bug"):
        with st.form("bug_report_form"):
            page = st.text_input("Page / Feature", st.session_state.get("bug_page", ""))
            bug = st.text_area("Describe the issue", st.session_state.get("bug_description", ""))
            severity = st.selectbox("Severity", ["Low", "Medium", "High"], index=st.session_state.get("bug_severity_index", 0))

            submitted = st.form_submit_button("Submit Bug")
            if submitted:
                st.session_state["bug_page"] = page
                st.session_state["bug_description"] = bug
                st.session_state["bug_severity_index"] = ["Low", "Medium", "High"].index(severity)

                try:
                    from utils import get_snowflake_connection
                    conn = get_snowflake_connection()
                    cursor = conn.cursor()

                    # Get email if logged in
                    user_email = st.session_state.get("user_email", None)

                    cursor.execute("""
                        INSERT INTO APP_BUGS (PAGE, DESCRIPTION, SEVERITY, SUBMITTED_AT, USER_EMAIL)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
                    """, (page, bug, severity, user_email))
                    conn.commit()

                    st.success("✅ Bug report submitted.")
                except Exception as e:
                    st.error(f"❌ Failed to submit bug: {e}")
                finally:
                    cursor.close()
                    conn.close()
