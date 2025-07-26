# xabuteo.py

import streamlit as st
from datetime import datetime
from utils import get_db_connection, ensure_profile_complete

query_params = st.query_params

# Set test mode in session state based on URL param
if "test" in query_params and query_params["test"][0] == "1":
    st.session_state["test_mode"] = True
    st.write("Test Mode:", st.session_state.get("test_mode", False))
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

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check for existing user (case-insensitive email)
        cursor.execute("""
            SELECT id, auth0_id, first_name, last_name, date_registered
            FROM registrations
            WHERE LOWER(email) = LOWER(%s)
        """, (email,))
        result = cursor.fetchone()
    
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
        if result is None:
            # Insert new user
            cursor.execute("""
                INSERT INTO registrations (
                    email, auth0_id, first_name, last_name,
                    date_registered, last_login, updated_at, updated_by
                )
                VALUES (%s, %s, %s, %s, CURDATE(), %s, %s, %s)
            """, (
                email, auth_id, first_name, last_name,
                now, now, email
            ))
        else:
            user_id, existing_auth0, existing_fname, existing_lname, existing_registered = result
    
            updates = []
            params = []
    
            if not existing_auth0:
                updates.append("auth0_id = %s")
                params.append(auth_id)
            if not existing_fname:
                updates.append("first_name = %s")
                params.append(first_name)
            if not existing_lname:
                updates.append("last_name = %s")
                params.append(last_name)
            if not existing_registered or str(existing_registered) in ("0000-00-00", "None"):
                updates.append("date_registered = CURDATE()")
    
            # Always update last_login and updated_by
            updates.append("last_login = %s")
            params.append(now)
            updates.append("updated_at = %s")
            params.append(now)
            updates.append("updated_by = %s")
            params.append(email)
    
            sql = f"""
                UPDATE registrations
                SET {', '.join(updates)}
                WHERE LOWER(email) = LOWER(%s)
            """
            params.append(email)
            cursor.execute(sql, params)
    
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    st.success(f"Welcome, {st.user.email}!")

    if st.button(
        "✨ Log out",
        type="primary",
        key="checkout-button",
        use_container_width=True,
    ):
        st.logout()

if st.session_state.get("test_mode"):
    from sidebar_utils import render_sidebar_widgets
    render_sidebar_widgets()
    st.json(st.user.to_dict())
