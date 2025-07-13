import streamlit as st
from datetime import date, timedelta
from contextlib import closing
from utils import get_db_connection, get_admin_club_ids

# ------------------------------------------------------------------------
def fetch_all(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()

# ------------------------------------------------------------------------
def add_new_event() -> None:
    club_ids = get_admin_club_ids()
    if not club_ids:
        return

    with st.expander("➕ Add New Event"):
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
            # ── look‑ups ---------------------------------------------------
            placeholders = ", ".join(["%s"] * len(club_ids))
            club_rows = fetch_all(
                cur,
                f"SELECT id, club_name FROM clubs WHERE id IN ({placeholders}) ORDER BY club_name",
                tuple(club_ids),
            )
            if not club_rows:
                st.error("⛔ Your admin account isn’t linked to any host clubs yet.")
                st.stop()

            club_name_to_id = {name: cid for cid, name in club_rows}
            club_names = list(club_name_to_id)

            event_types = [
                r[0]
                for r in fetch_all(
                    cur,
                    "SELECT list_value FROM ref_lookup "
                    "WHERE list_type = 'event_type' ORDER BY list_order",
                )
            ]

        # ── build & process form -----------------------------------------
        with st.form("add_event_form", clear_on_submit=False):
            # Keys let us wipe the widgets later
            c1, c2 = st.columns(2)
            title = c1.text_input("Event Title", key="f_title")
            event_type = c2.selectbox("Event Type", event_types, key="f_type")

            c1, c2 = st.columns(2)
            start_date = c1.date_input("Start Date", key="f_start")
            end_date   = c2.date_input("End Date",   key="f_end")

            c1, c2 = st.columns(2)
            reg_open = c1.date_input("Registration Open Date",  key="f_reg_open")
            reg_close= c2.date_input("Registration Close Date", key="f_reg_close")

            c1, c2 = st.columns(2)
            location = c1.text_input("Location", key="f_loc")
            host_club = c2.selectbox(
                "Host Club",
                club_names,
                index=0 if len(club_names) == 1 else 0,
                key="f_host",
            )
            host_club_id = club_name_to_id.get(host_club)

            c1, c2, c3 = st.columns(3)
            event_open    = c1.checkbox("Open",    key="f_open")
            event_women   = c1.checkbox("Women",   key="f_women")
            event_junior  = c2.checkbox("Junior",  key="f_junior")
            event_veteran = c2.checkbox("Veteran", key="f_vet")
            event_teams   = c3.checkbox("Teams",   key="f_team")

            event_email = st.text_input("Contact Email", key="f_email")
            comments    = st.text_area("Comments", key="f_comments")

            submitted = st.form_submit_button("Add Event")

            # ── validation ------------------------------------------------
            if submitted:
                errs = []
                if not title:
                    errs.append("• Title is required")
                if start_date > end_date:
                    errs.append("• Start Date must not be after End Date")
                if reg_open > reg_close:
                    errs.append("• Registration Open must be on/before Registration Close")
                if not host_club_id:
                    errs.append("• Please select a host club")

                if errs:
                    st.error("❌ Please fix the following:\n" + "\n".join(errs))
                    st.stop()

                # ── insert -------------------------------------------------
                try:
                    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:
                        cur.execute(
                            """
                            INSERT INTO events (
                                event_title, event_type, event_location,
                                event_start_date, event_end_date,
                                reg_open_date, reg_close_date,
                                event_email, event_open, event_women,
                                event_junior, event_veteran, event_teams,
                                event_comments, host_club_id
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (
                                title, event_type, location,
                                start_date, end_date,
                                reg_open, reg_close,
                                event_email, event_open, event_women,
                                event_junior, event_veteran, event_teams,
                                comments, host_club_id,
                            ),
                        )
                        conn.commit()
                    st.success("✅ Event added successfully.")

                    # ── clear widgets & refresh --------------------------
                    for k in (
                        "f_title", "f_type", "f_start", "f_end",
                        "f_reg_open", "f_reg_close", "f_loc", "f_host",
                        "f_open", "f_women", "f_junior", "f_vet", "f_team",
                        "f_email", "f_comments",
                    ):
                        st.session_state.pop(k, None)      # remove saved value

                except Exception as exc:
                    st.error(f"❌ Failed to add event: {exc}")
