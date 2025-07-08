import os
import snowflake.connector
import mysql.connector
import streamlit as st
from datetime import date

# Snowflake connection from st.secrets
def get_db_connection():
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        account=st.secrets["snowflake"]["account"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"]
    )

# MySQL connection from st.secrets
def get_db_connectionX():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
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

def get_admin_club_ids() -> list:
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        # Get user ID from registrations table
        cursor.execute("""
            SELECT id FROM registrations WHERE email = %s
        """, (st.user.email,))
        user_row = cursor.fetchone()
        if not user_row:
            return []  # User not found

        user_id = user_row[0]

        # Get active admin club_ids
        cursor.execute("""
            SELECT club_id FROM club_user_admin 
            WHERE user_id = %s
            AND %s BETWEEN valid_from AND valid_to
        """, (user_id, date.today()))
        admin_club_rows = cursor.fetchall()

        return [row[0] for row in admin_club_rows]

    finally:
        cursor.close()
        conn.close()
