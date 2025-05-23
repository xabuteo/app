import streamlit as st
import re
from utils import get_snowflake_connection, hash_password, check_password, send_email
from datetime import date

st.set_page_config(page_title="Xabuteo", layout="wide", initial_sidebar_state="expanded")

st.title("🏠 Welcome to Xabuteo")
st.markdown("Welcome to the world's premier table football online application!")

# 👤 If already logged in, redirect to dashboard
if st.session_state.get("user_email"):
    st.success(f"🔓 Logged in as {st.session_state['user_name']}")
    st.info("You can now access the app pages from the sidebar.")
    if st.button("Log out"):
        st.session_state.clear()
        st.success("🔒 You have been logged out.")
        st.rerun()
    st.stop()

# 🔐 Login Section
st.subheader("🔐 Login")
login_email = st.text_input("Email Address", key="login_email")
login_password = st.text_input("Password", type="password", key="login_password")

def verify_user(email, password):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM registrations WHERE email = %s", (email,))
        result = cursor.fetchone()
        if result:
            return check_password(password, result[0])
        return False
    except Exception as e:
        st.error(f"Login error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if st.button("Login"):
    if login_email and login_password:
        if verify_user(login_email, login_password):
            st.session_state["user_email"] = login_email
            st.session_state["user_name"] = login_email.split("@")[0].capitalize()
            st.success(f"✅ Welcome back, {st.session_state['user_name']}!")
            st.rerun()
        else:
            st.error("❌ Invalid email or password.")
    else:
        st.warning("Please enter both email and password.")

# 📝 Registration Section
st.markdown("---")
with st.expander("📋 Register for an account"):
    with st.form("registration_form"):
        st.subheader("Enter your details:")
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
        with col2:
            last_name = st.text_input("Last Name")
        with col1:
            date_of_birth = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
        with col2:
            gender = st.selectbox("Gender", ["M", "F", "Other"])
        reg_email = st.text_input("Email Address")
        reg_password = st.text_input("Password", type="password")

        # Real-time validation messages
        if reg_email and not is_valid_email(reg_email):
            st.error("❌ Invalid email format.")
        if reg_password and len(reg_password) < 8:
            st.error("🔒 Password must be at least 8 characters long.")
    
        # Check overall validity
        all_fields_valid = all([first_name, last_name, reg_email, reg_password]) \
                           and is_valid_email(reg_email) \
                           and len(reg_password) >= 8
        
        def insert_registration(data):
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM registrations WHERE email = %s", (data['email'],))
                if cursor.fetchone()[0] > 0:
                    st.warning("🚫 This email is already registered.")
                    return False

                cursor.execute("""
                    INSERT INTO registrations (first_name, last_name, date_of_birth, gender, email, password)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    data['first_name'],
                    data['last_name'],
                    data['date_of_birth'].strftime('%Y-%m-%d'),
                    data['gender'],
                    data['email'],
                    hash_password(data['password'])
                ))
                conn.commit()
                return True
            except Exception as e:
                st.error(f"Error saving to Snowflake: {e}")
                return False
            finally:
                cursor.close()
                conn.close()

        def send_welcome_email(to_email, first_name):
            subject = "🎉 Welcome to Xabuteo!"
            message = f"""\
Hello {first_name},

Welcome to Xabuteo – the world's premier table football platform!

We're thrilled to have you join our community.

Kind regards,  
The Xabuteo Team
"""
            try:
                send_email(to_email, subject, message)
                return True
            except Exception as e:
                st.warning(f"⚠️ Unable to send welcome email: {e}")
                return False

        submitted = st.form_submit_button("Register")
        if submitted:
            if all([first_name, last_name, reg_email, reg_password]):
                form_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": date_of_birth,
                    "gender": gender,
                    "email": reg_email,
                    "password": reg_password
                }
                if insert_registration(form_data):
                    st.success("🎉 Registration successful!")
                    send_welcome_email(reg_email, first_name)
                    st.session_state["user_email"] = reg_email
                    st.session_state["user_name"] = f"{first_name} {last_name}"
                    st.success(f"🔓 Logged in as {st.session_state['user_name']}")
                    st.rerun()
            else:
                st.warning("Please fill in all required fields.")
