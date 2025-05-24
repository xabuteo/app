import streamlit as st
from auth import login
from utils import get_snowflake_connection
from datetime import date

st.set_page_config(page_title="Xabuteo", layout="centered")
st.title("🏓 Welcome to Xabuteo")

auth0_response = login()

if auth0_response:
    user = auth0_response["user"]
    email = user["email"]
    name = user.get("name", email.split("@")[0])
    sub = user["sub"]

    st.session_state["user_email"] = email
    st.session_state["user_name"] = name
    st.session_state["auth0_sub"] = sub

    st.success(f"✅ Logged in as {name}")

    # Track user registration in DB
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM XABUTEO.PUBLIC.REGISTRATIONS WHERE email = %s", (email,))
        if cursor.fetchone()[0] == 0:
            first_name, *last_parts = name.split()
            last_name = " ".join(last_parts) if last_parts else ""
            cursor.execute("""
                INSERT INTO XABUTEO.PUBLIC.REGISTRATIONS (first_name, last_name, email, date_registered, auth0_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (first_name, last_name, email, date.today(), sub))
            conn.commit()
            st.info("🆕 Registered in Xabuteo!")
    except Exception as e:
        st.error(f"❌ DB Error: {e}")
    finally:
        cursor.close()
        conn.close()
else:
    st.info("🔐 Please log in to access the app.")
