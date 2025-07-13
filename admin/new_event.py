import streamlit as st
from datetime import date, timedelta
from contextlib import closing

from utils import get_db_connection, get_admin_club_ids


# ------------------------------------------------------------------------
def fetch_all(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def add_new_event() -> None:
    """Form that lets club admins create a new event."""
    club_ids = get_admin_club_ids()

    # ── Only admins can proceed ──────────────────────────────────────────
    if not club_ids:
        return  # show nothing if user isn’t a club admin

    with st.expander("➕ Add New Event"):
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:

            # ── 1.  Look up host‑club choices & event types up front ─────
            placeholders = ", ".join(["%s"] * len(club_ids))
            host_club_rows = fetch_all(
                cur,
                f"""
                SELECT id, club_name
                FROM clubs
                WHERE id IN ({placeholders})
                ORDER BY club_name
                """,
                tuple(club_ids),
            )

            if not host_club_rows:
                st.error("⛔ Your admin account isn’t linked to any host clubs yet.")
                st.stop()

            club_name_to_id = {name: cid for cid, name in host_club_rows}
            club_names = list(club_name_to_id)

            event_types = [
                r[0]
                for r in fetch_all(
                    cur,
                    """
                    SELECT list_value
                    FROM ref_lookup
                    WHERE list_type = 'event_type'
                    ORDER BY list_order
                    """,
                )
            ]

            # ── 2.  Build the form ───────────────────────────────────────
            with st.form("add_event_form"):
                # Basic info
                c1, c2 = st.columns(2)
                title = c1.text_input("Event Title")
                event_type = c2.selectbox("Event Type", event_types)

                c1, c2 = st.columns(2)
                start_date = c1.date_input("Start Date")
                end_date = c2.date_input("End Date")

                c1, c2 = st.columns(2)
                reg_open_date = c1.date_input("Registration Open Date")
                reg_close_date = c2.date_input("Registration Close Date")

                # Location + Host club
                c1, c2 = st.columns(2)
                location = c1.text_input("Location")
                selected_club = c2.selectbox(
                    "Host Club",
                    club_names,
                    index=0 if len(club_names) == 1 else 0,
                )
                host_club_id = club_name_to_id.get(selected_club)

                # Divisions
                c1, c2, c3 = st.columns(3)
                event_open = c1.checkbox("Open")
                event_women = c1.checkbox("Women")
                event_junior = c2.checkbox("Junior")
                event_veteran = c2.checkbox("Veteran")
                event_teams = c3.checkbox("Teams")

                event_email = st.text_input("Contact Email")
                comments = st.text_area("Comments")

                submitted = st.form_submit_button("Add Event")

                # ── 3.  Validation & insert ────────────────────────────
                if submitted:
                    errors = []

                    if not title:
                        errors.append("• Title is required")
                    if start_date > end_date:
                        errors.append("• Start Date must not be after End Date")
                    if reg_open_date > reg_close_date:
                        errors.append("• Registration Open must be on/before Registration Close")
                    if reg_close_date >= start_date:
                        errors.append("• Registration must close **before** the event starts")
                    if not host_club_id:
                        errors.append("• Please select a host club")

                    if errors:
                        st.error("❌ Please fix the following:\n" + "\n".join(errors))
                        st.stop()

                    try:
                        cur.execute(
                            """
                            INSERT INTO events (
                                event_title, event_type, event_location,
                                event_start_date, event_end_date,
                                reg_open_date, reg_close_date,
                                event_email, event_open, event_women,
                                event_junior, event_veteran, event_teams,
                                event_comments, host_club_id
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                title,
                                event_type,
                                location,
                                start_date,
                                end_date,
                                reg_open_date,
                                reg_close_date,
                                event_email,
                                event_open,
                                event_women,
                                event_junior,
                                event_veteran,
                                event_teams,
                                comments,
                                host_club_id,
                            ),
                        )
                        conn.commit()
                        st.success("✅ Event added successfully.")
                        st.rerun()
                    except Exception as exc:
                        conn.rollback()
                        st.error(f"❌ Failed to add event: {exc}")
