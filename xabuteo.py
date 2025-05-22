import streamlit as st
from utils import get_snowflake_connection, hash_password

st.set_page_config(page_title="Xabuteo", layout="wide", initial_sidebar_state="expanded")

st.title("🏠 Welcome to Xabuteo")
st.markdown("""Welcome to the world's premier table football online application!""")

def show():
    if st.session_state.get("user_email"):
        st.info("🔓 You are already registered and logged in.")
        return

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

    with st.form("registration_form"):
        st.subheader("Enter your details:")
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        date_of_birth = st.date_input("Date of Birth")
        gender = st.selectbox("Gender", ["M", "F", "Other"])
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button("Register")
        if submitted:
            if all([first_name, last_name, email, password]):
                form_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": date_of_birth,
                    "gender": gender,
                    "email": email,
                    "password": password
                }
                if insert_registration(form_data):
                    st.success("🎉 Registration successful!")
            else:
                st.warning("Please fill in all required fields.")
