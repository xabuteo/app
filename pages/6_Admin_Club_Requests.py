import streamlit as st
from utils import get_snowflake_connection

def show():
    st.title("🗂️ Club Requests")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT pc.id, r.first_name || ' ' || r.last_name AS player_name, 
                   c.club_name, pc.valid_from, pc.valid_to, pc.player_status
            FROM xabuteo.public.player_club pc
            JOIN xabuteo.public.registrations r ON pc.player_id = r.id
            JOIN xabuteo.public.clubs c ON pc.club_id = c.id
            WHERE pc.player_status = 'Pending'
            ORDER BY pc.valid_from DESC
        """)
        rows = cursor.fetchall()
        cols = [desc[0].lower() for desc in cursor.description]

        if not rows:
            st.info("✅ No pending club requests.")
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
                            UPDATE xabuteo.public.player_club
                            SET player_status = 'Approved'
                            WHERE id = %s
                        """, (request["id"],))
                        conn.commit()
                        st.success(f"Approved {request['club_name']} for {request['player_name']}")
                        st.rerun()

                with col2:
                    if st.button("❌ Reject", key=f"reject_{request['id']}"):
                        cursor.execute("""
                            UPDATE xabuteo.public.player_club
                            SET player_status = 'Rejected'
                            WHERE id = %s
                        """, (request["id"],))
                        conn.commit()
                        st.warning(f"Rejected {request['club_name']} for {request['player_name']}")
                        st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading requests: {e}")
    finally:
        cursor.close()
        conn.close()
show()        
