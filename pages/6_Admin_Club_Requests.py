import streamlit as st
from datetime import date
from utils import get_snowflake_connection

def show():
    st.title("🗂️ Club Requests")

    if not st.user.is_logged_in:
        st.warning("🔒 Please log in to access this page.")
        return

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Get user ID
        cursor.execute("""
            SELECT id FROM registrations WHERE email = %s
        """, (st.user.email,))
        user_row = cursor.fetchone()
        if not user_row:
            st.error("❌ User not found.")
            #return
            user_id = 201
        else:
            user_id = user_row[0]

        # Get list of active clubs this user administers
        cursor.execute("""
            SELECT club_id FROM club_user_admin 
            WHERE user_id = %s AND %s BETWEEN valid_from AND valid_to
        """, (user_id, date.today()))
        admin_club_rows = cursor.fetchall()
        admin_club_ids = [row[0] for row in admin_club_rows]

        if not admin_club_ids:
            st.warning("⛔ You are not currently an active club admin.")
            return

        # Fetch pending player club requests only for the admin's clubs
        format_ids = ",".join(["%s"] * len(admin_club_ids))
        query = f"""
            SELECT pc.id, r.first_name || ' ' || r.last_name AS player_name, 
                   c.club_name, pc.valid_from, pc.valid_to, pc.player_status
            FROM player_club pc
            JOIN registrations r ON pc.player_id = r.id
            JOIN clubs c ON pc.club_id = c.id
            WHERE pc.player_status = 'Pending' AND pc.club_id IN ({format_ids})
            ORDER BY pc.valid_from DESC
        """
        cursor.execute(query, tuple(admin_club_ids))
        rows = cursor.fetchall()
        cols = [desc[0].lower() for desc in cursor.description]

        if not rows:
            st.info("✅ No pending club requests for your clubs.")
            return

        for row in rows:
            request = dict(zip(cols, row))

            with st.container():
                st.markdown(
                    f"""
                    <div style="border: 2px solid #3dc2d4; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                        <strong>👤 Player:</strong> {request['player_name']}<br>
                        <strong>🏟️ Club:</strong> {request['club_name']}<br>
                        <strong>📅 Valid From:</strong> {request['valid_from']}<br>
                        <strong>📅 Valid To:</strong> {request['valid_to']}<br>
                        <strong>🕒 Status:</strong> {request['player_status']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ Approve", key=f"approve_{request['id']}"):
                        cursor.execute("""
                            UPDATE player_club
                            SET player_status = 'Approved'
                            WHERE id = %s
                        """, (request["id"],))
                        conn.commit()
                        st.success(f"✅ Approved {request['club_name']} for {request['player_name']}")
                        st.rerun()

                with col2:
                    if st.button("❌ Reject", key=f"reject_{request['id']}"):
                        cursor.execute("""
                            UPDATE player_club
                            SET player_status = 'Rejected'
                            WHERE id = %s
                        """, (request["id"],))
                        conn.commit()
                        st.warning(f"❌ Rejected {request['club_name']} for {request['player_name']}")
                        st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading requests: {e}")
    finally:
        cursor.close()
        conn.close()

# For multipage apps
if __name__ == "__main__":
    show()
