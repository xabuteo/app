import streamlit as st
import pandas as pd
from utils import get_db_connection, ensure_profile_complete, get_admin_club_ids
from datetime import date

def show():
    st.title("🏟️ My Clubs")

    ensure_profile_complete()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get Player ID for logged-in user
        cursor.execute(
            "SELECT ID FROM REGISTRATIONS WHERE EMAIL = %s", 
            (st.user.email,)
        )
        player_row = cursor.fetchone()
        if not player_row:
            st.error("❌ Could not find player ID.")
            return
        player_id = player_row[0]

        # --- Display PLAYER_CLUB_V view ---
        cursor.execute(
            "SELECT * FROM PLAYER_CLUB_V WHERE EMAIL = %s", 
            (st.user.email,)
        )
        rows = cursor.fetchall()
        columns = [desc[0].lower() for desc in cursor.description]
        df = pd.DataFrame(rows, columns=columns)

        expected_cols = ['club_code', 'club_name', 'player_status', 'valid_from', 'valid_to']
        actual_cols = df.columns.tolist()

        if all(col in actual_cols for col in expected_cols):
            if not df.empty:
                df = df[expected_cols]

                def is_active(row):
                    if pd.notnull(row['valid_from']) and pd.notnull(row['valid_to']):
                        return row['valid_from'] <= date.today() <= row['valid_to']
                    return False

                df['highlight'] = df.apply(is_active, axis=1)
                df = df.sort_values(by='valid_from', ascending=False)

                styled_df = df.drop(columns='highlight').style.apply(
                    lambda x: ['font-weight: bold' if h else '' for h in df['highlight']], axis=0
                )
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ You are not currently associated with any clubs.")
        else:
            st.warning("⚠️ View is missing required columns.")
            st.info("Columns found: " + ", ".join(actual_cols))
    except Exception as e:
        st.error(f"❌ Error loading clubs: {e}")
    finally:
        cursor.close()
        conn.close()

def show_request_club():
    # --- Request New Club ---
    st.markdown("---")
    with st.expander("➕ Request New Club"):
        # Associations dropdown
        cursor.execute("""
            SELECT id, association_name 
            FROM associations 
            ORDER BY association_name
        """)
        assoc_data = cursor.fetchall()
        if assoc_data:
            assoc_options = {name: id for id, name in assoc_data}
            assoc_name = st.selectbox("Select Association", list(assoc_options.keys()))

            if assoc_name:
                assoc_id = assoc_options[assoc_name]
                cursor.execute("""
                    SELECT id, club_name 
                    FROM clubs 
                    WHERE association_id = %s 
                    ORDER BY club_name
                """, (assoc_id,))
                club_data = cursor.fetchall()

                if club_data:
                    club_options = {name: id for id, name in club_data}
                    club_name = st.selectbox("Select Club", list(club_options.keys()))
                    valid_from = st.date_input("Valid From", date.today())
                    valid_to = st.date_input("Valid To", date.today())

                    if st.button("Submit Club Request"):
                        club_id = club_options[club_name]
                        try:
                            cursor.execute("""
                                INSERT INTO PLAYER_CLUB 
                                (PLAYER_ID, CLUB_ID, VALID_FROM, VALID_TO)
                                VALUES (%s, %s, %s, %s)
                            """, (player_id, club_id, valid_from, valid_to))
                            conn.commit()
                            st.success("✅ Club request submitted successfully.")
                        except Exception as e:
                            st.error(f"❌ Failed to submit request: {e}")
                else:
                    st.info("ℹ️ No clubs found for the selected association.")
        else:
            st.info("ℹ️ No associations available at the moment.")

def show_admin():
    club_ids = get_admin_club_ids()
    if not club_ids:
        st.warning("⛔ You are not currently an active club admin.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch pending player club requests only for the admin's clubs
        format_ids = ",".join(["%s"] * len(club_ids))
        query = f"""
            SELECT pc.id, r.first_name || ' ' || r.last_name AS player_name, 
                   c.club_name, pc.valid_from, pc.valid_to, pc.player_status
            FROM player_club pc
            JOIN registrations r ON pc.player_id = r.id
            JOIN clubs c ON pc.club_id = c.id
            WHERE pc.player_status = 'Pending' AND pc.club_id IN ({format_ids})
            ORDER BY pc.valid_from DESC
        """
        cursor.execute(query, tuple(club_ids))
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

    finally:
        cursor.close()
        conn.close()
        
# Required for multipage apps
if __name__ == "__main__":
    show()
    st.write("If you need to register or change clubs, please contact the club administrator.")
    if st.session_state.get("test_mode"):
        show_request_club()
        show_admin()
        from sidebar_utils import render_sidebar_widgets
        render_sidebar_widgets()

