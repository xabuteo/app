import streamlit as st
from utils import get_db_connection

def render(event_id, event_status, user_email):
    cols = st.columns(5)  

    if event_status == "Pending":
        with cols[0]:
            if st.button("✅ Approve"):
                update_status(event_id, user_email, "Approved")

    if event_status not in ["Cancelled", "Pending"]:
        with cols[0]:
            if st.button("✅ Complete"):
                update_status(event_id, user_email, "Complete")

    if event_status != "Cancelled":
        with cols[1]:
            if st.button("❌ Cancel"):
                update_status(event_id, user_email, "Cancelled")

def update_status(event_id, user_email, new_status):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events
            SET event_status = %s,
                update_timestamp = CURRENT_TIMESTAMP,
                update_by = %s
            WHERE id = %s
        """, (new_status, user_email, event_id))
        conn.commit()
        st.success(f"✅ Event status updated to '{new_status}'.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to update event status: {e}")
    finally:
        cursor.close()
        conn.close()
