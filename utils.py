import os
import snowflake.connector
import bcrypt
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from utils import get_snowflake_connection

SNOWFLAKE_CONFIG = {
    'user': os.environ.get('user'),
    'password': os.environ.get('password'),
    'account': os.environ.get('account'),
    'warehouse': os.environ.get('warehouse'),
    'database': os.environ.get('database'),
    'schema': os.environ.get('schema')
}

def send_email(to_email, subject, message):
    try:
        email_config = st.secrets["email"]

        from_email = email_config["from_email"]
        password = email_config["password"]
        smtp_server = email_config.get("smtp_server", "smtp.gmail.com")
        smtp_port = email_config.get("smtp_port", 587)

        # Create MIME message
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "plain"))

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)

        return True

    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_CONFIG['user'],
        password=SNOWFLAKE_CONFIG['password'],
        account=SNOWFLAKE_CONFIG['account'],
        warehouse=SNOWFLAKE_CONFIG['warehouse'],
        database=SNOWFLAKE_CONFIG['database'],
        schema=SNOWFLAKE_CONFIG['schema']
    )

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def ensure_profile_complete():
    """Check that the current user's profile is complete in the registrations table."""
    if "user_email" not in st.session_state:
        st.warning("🔐 You are not logged in.")
        st.stop()

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT first_name, last_name, date_of_birth, gender
            FROM xabuteo.public.registrations
            WHERE email = %s
        """, (st.session_state.user_email,))
        row = cursor.fetchone()

        if not row or not all(row):
            st.warning("⚠️ Your profile is incomplete. Please complete it before continuing.")
            st.markdown("➡️ [Go to your profile page](./2_Profile)")
            st.stop()
    except Exception as e:
        st.error(f"❌ Failed to verify profile: {e}")
        st.stop()
    finally:
        cursor.close()
        conn.close()
