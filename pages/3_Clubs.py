import streamlit as st
import pandas as pd
from datetime import date, timedelta
from contextlib import closing

from utils import (
    get_db_connection,
    ensure_profile_complete,
    get_admin_club_ids,
)

def fetch_one(cursor, query, params=()):
    cursor.execute(query, params)
    return cursor.fetchone()

def fetch_all(cursor, query, params=()):
    cursor.execute(query, params)
    return cursor.fetchall(), [d[0].lower() for d in cursor.description]

# ------------------------------------------------------------------ SHOW MAIN
def show():
    st.title("🏟️ My Clubs")
    ensure_profile_complete()

    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cursor:
        # -------------------------------------------------- current player
        player = fetch_one(cursor,
            "SELECT id FROM registrations WHERE email = %s",
            (st.user.email,)
        )
        if not player:
            st.error("❌ Could not find player ID.")
            return
        user_id = player[0]

        # -------------------------------------------------- club view
        rows, cols = fetch_all(
            cursor,
            "SELECT * FROM player_club_v WHERE email = %s",
            (st.user.email,)
        )
        
        expected = ['club_code', 'club_name', 'player_status',
                    'valid_from', 'valid_to']
        if not all(c in cols for c in expected):
            st.warning("⚠️ View is missing required columns.")
            st.info("Columns found: " + ", ".join(cols))
            return
        
        df = pd.DataFrame(rows, columns=cols)
        if df.empty:
            st.info("ℹ️ You are not currently associated with any clubs.")
        else:
            df = (
                df[expected]
                .sort_values('valid_from', ascending=False)
                .reset_index(drop=True)
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

        # extra pages in test‑mode
        if st.session_state.get("test_mode"):
            show_request_club(cursor, conn, user_id)
            from sidebar_utils import render_sidebar_widgets
            render_sidebar_widgets()

        show_admin(cursor, conn)

# -------------------------------------------------- REQUEST NEW CLUB
def show_request_club(cursor, conn, user_id):
    st.markdown("---")
    with st.expander("➕ Request New Club"):
        assoc_rows, _ = fetch_all(cursor,
            "SELECT id, association_name FROM associations ORDER BY association_name"
        )
        if not assoc_rows:
            st.info("ℹ️ No associations available at the moment.")
            return

        assoc_map = {name: id_ for id_, name in assoc_rows}
        assoc_name = st.selectbox("Select Association", assoc_map.keys())
        if not assoc_name:
            return

        club_rows, _ = fetch_all(cursor,
            "SELECT id, club_name FROM clubs WHERE association_id = %s ORDER BY club_name",
            (assoc_map[assoc_name],)
        )
        if not club_rows:
            st.info("ℹ️ No clubs found for the selected association.")
            return

        club_map = {name: id_ for id_, name in club_rows}
        club_name = st.selectbox("Select Club", club_map.keys())

        col1, col2 = st.columns(2)
        with col1:
            valid_from = st.date_input("Valid From", date.today())
        with col2:
            valid_to   = st.date_input("Valid To",   date.today() + timedelta(days=365))

        if valid_to < valid_from:
            st.error("❌ 'Valid To' must be on or after 'Valid From'.")
            return

        if st.button("Submit Club Request"):
            try:
                cursor.execute("""
                    INSERT INTO player_club (user_id, club_id, valid_from, valid_to)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, club_map[club_name], valid_from, valid_to))
                conn.commit()
                st.success("✅ Club request submitted successfully.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Failed to submit request: {e}")

# -------------------------------------------------- ADMIN (approve / reject)
def show_admin(cursor, conn):
    club_ids = get_admin_club_ids()
    if not club_ids:
        st.warning("⛔ You are not currently an active club admin.")
        return

    placeholders = ", ".join(["%s"] * len(club_ids))
    
    # --- Approvals Section ---
    rows, cols = fetch_all(cursor, f"""
        SELECT pc.id,
               TRIM(CONCAT_WS(' ', r.first_name, r.last_name)) AS player_name,
               c.club_name, pc.valid_from, pc.valid_to, pc.player_status
        FROM   player_club pc
        JOIN   registrations r ON pc.user_id = r.id
        JOIN   clubs         c ON pc.club_id   = c.id
        WHERE  pc.player_status = 'Pending'
        AND    pc.club_id IN ({placeholders})
        ORDER  BY pc.valid_from DESC
    """, tuple(club_ids))

    if rows:
        st.markdown("### ✅ Pending Approvals")
        for rec in map(lambda r: dict(zip(cols, r)), rows):
            with st.container(border=True):
                st.markdown(
                    f"""
                    **👤 Player:** {rec['player_name']}  
                    **🏟️ Club:** {rec['club_name']}  
                    **📅 Valid:** {rec['valid_from']} → {rec['valid_to']}  
                    **🕒 Status:** {rec['player_status']}
                    """
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Approve", key=f"app_{rec['id']}"):
                        cursor.execute("UPDATE player_club SET player_status = 'Approved' WHERE id = %s", (rec['id'],))
                        conn.commit()
                        st.success("Approved.")
                        st.rerun()
                with col_b:
                    if st.button("❌ Reject", key=f"rej_{rec['id']}"):
                        cursor.execute("UPDATE player_club SET player_status = 'Rejected' WHERE id = %s", (rec['id'],))
                        conn.commit()
                        st.warning("Rejected.")
                        st.rerun()
    else:
        st.info("✅ No pending club requests for your clubs.")

    # --- Club Members Section (ALWAYS SHOWN) ---
    st.markdown("### 👥 Club Members")

    rows, cols = fetch_all(cursor, f"""
        SELECT
            id, first_name, last_name, email, date_of_birth, gender,
            player_status, valid_from, valid_to, club_code, club_name
        FROM player_club_v
        WHERE club_code IN ({placeholders})
        ORDER BY club_name, last_name, first_name
    """, tuple(club_ids))

    if not rows:
        st.info("ℹ️ No members found in your clubs.")
        return

    df_all = pd.DataFrame(rows, columns=cols)
    grouped = df_all.groupby("club_name")

    for club_name, club_df in grouped:
        with st.expander(f"🏟️ {club_name} ({len(club_df)} players)", expanded=False):
            club_df_disp = (
                club_df[
                    ['first_name', 'last_name', 'email', 'date_of_birth',
                     'gender', 'player_status', 'valid_from', 'valid_to']
                ]
                .sort_values("last_name")
                .reset_index(drop=True)
            )
            st.dataframe(club_df_disp, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ ENTRY
if __name__ == "__main__":
    show()
    st.write(
        "If you need to register or change clubs, please contact the club administrator."
    )
