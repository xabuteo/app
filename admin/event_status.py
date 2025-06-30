import streamlit as st
from utils import get_snowflake_connection

def render(event_id, event_status, user_email):
    if event_status == "Pending":
        if st.button("✅ Approve"):
            update_status(event_id, user_email, "Approved")
    if event_status != "Cancelled":
        if st.button("❌ Cancel"):
            update_status(event_id, user_email, "Cancelled")
    if event_status != "Cancelled" and event_status != "Pending":
        if st.button("✅ Complete"):
            update_status(event_id, user_email, "Complete")

def update_status(event_id, user_email, new_status):
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE EVENTS
            SET EVENT_STATUS = %s,
                UPDATE_TIMESTAMP = CURRENT_TIMESTAMP,
                UPDATE_BY = %s
            WHERE ID = %s
        """, (new_status, user_email, event_id))
        conn.commit()
        st.success(f"✅ Event status updated to '{new_status}'.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to update event status: {e}")
    finally:
        cursor.close()
        conn.close()
