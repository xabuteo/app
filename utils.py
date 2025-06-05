import os
import snowflake.connector
import streamlit as st

SNOWFLAKE_CONFIG = {
    'user': os.environ.get('user'),
    'password': os.environ.get('password'),
    'account': os.environ.get('account'),
    'warehouse': os.environ.get('warehouse'),
    'database': os.environ.get('database'),
    'schema': os.environ.get('schema')
}

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_CONFIG['user'],
        password=SNOWFLAKE_CONFIG['password'],
        account=SNOWFLAKE_CONFIG['account'],
        warehouse=SNOWFLAKE_CONFIG['warehouse'],
        database=SNOWFLAKE_CONFIG['database'],
        schema=SNOWFLAKE_CONFIG['schema']
    )

def ensure_profile_complete():
    """Check that the current user's profile is complete in the registrations table."""
    if not st.user.is_logged_in:
        st.warning("🔐 You are not logged in.")
        st.stop()

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, first_name, last_name, date_of_birth, gender
            FROM registrations
            WHERE email = %s
        """, (st.user.email,))
        row = cursor.fetchone()

        if not row or not all(row):
            st.warning("⚠️ Your profile is incomplete. Please complete it before continuing.")
            #st.markdown("➡️ [Go to your profile page](./2_Profile)")
            st.stop()
    except Exception as e:
        st.error(f"❌ Failed to verify profile: {e}")
        st.stop()
    finally:
        cursor.close()
        conn.close()

import streamlit as st
from utils import get_snowflake_connection

def get_userid():
    try:
        if not getattr(st, "user", None) or not getattr(st.user, "email", None):
            st.warning("User not logged in or email not available.")
            return None

        conn = get_snowflake_connection()
        cursor = conn.cursor()

        query = """
            SELECT id
            FROM registrations
            WHERE email = %s
        """
        cursor.execute(query, (st.user.email,))
        row = cursor.fetchone()

        return row[0] if row else None

    except Exception as e:
        st.error(f"Error fetching user ID: {e}")
        return None

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


