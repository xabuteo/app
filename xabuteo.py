# app.py
import streamlit as st
import datetime
from utils import get_snowflake_connection
from auth0_component import login_button  # from previous setup

st.set_page_config(page_title="Xabuteo", layout="centered")

st.title("🏓 Welcome to Xabuteo")

auth0_result = login_button()

if auth0_result:
    user_info = auth0_result["user"]
    email = user_info.get("email")
    name = user_info.get("name", "")
    sub = user_info.get("sub")  # Auth0 unique ID

    if email:
        st.success(f"✅ Logged in as {email}")
        st.session_state["user_email"] = email
        st.session_state["user_name"] = name
        st.session_state["auth0_sub"] = sub

        # Track registration in DB
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        try:
            # Check if user already registered
            cursor.execute("SELECT COUNT(*) FROM XABUTEO.PUBLIC.REGISTRATIONS WHERE email = %s", (email,))
            exists = cursor.fetchone()[0] > 0

            if not exists:
                first_name, *last_parts = name.split(" ")
                last_name = " ".join(last_parts) if last_parts else ""

                cursor.execute("""
                    INSERT INTO XABUTEO.PUBLIC.REGISTRATIONS (first_name, last_name, email, date_registered, auth0_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (first_name, last_name, email, datetime.date.today(), sub))
                conn.commit()
                st.info("🆕 Registered in Xabuteo database!")

        except Exception as e:
            st.error(f"❌ Error tracking registration: {e}")
        finally:
            cursor.close()
            conn.close()

    else:
        st.error("⚠️ Could not retrieve user email.")
else:
    st.info("🔐 Please log in above.")
