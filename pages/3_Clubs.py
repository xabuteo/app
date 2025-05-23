import streamlit as st
import pandas as pd
from utils import get_snowflake_connection
from datetime import date

def show():
    st.title("🏟️ My Clubs")

    if "user_email" not in st.session_state:
        st.warning("🔒 Please log in to view your clubs.")
        return

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Get Player ID for logged-in user
        cursor.execute("SELECT ID FROM XABUTEO.PUBLIC.REGISTRATIONS WHERE EMAIL = %s", (st.session_state["user_email"],))
        player_row = cursor.fetchone()
        if not player_row:
            st.error("❌ Could not find player ID.")
            return
        player_id = player_row[0]

        # --- Display PLAYER_CLUB_V view ---
        cursor.execute("SELECT * FROM XABUTEO.PUBLIC.PLAYER_CLUB_V WHERE EMAIL = %s", (st.session_state["user_email"],))
        rows = cursor.fetchall()
        columns = [desc[0].lower() for desc in cursor.description]  # lowercase for matching
        df = pd.DataFrame(rows, columns=columns)

        expected_cols = ['club_code', 'club_name', 'player_status', 'valid_from', 'valid_to']
        actual_cols = df.columns.tolist()

        if all(col in actual_cols for col in expected_cols):
            df = df[expected_cols]
            df['highlight'] = df.apply(
                lambda row: row['valid_from'] <= date.today() <= row['valid_to'], axis=1
            )
            df = df.sort_values(by='valid_from', ascending=False)
            styled_df = df.drop(columns='highlight').style.apply(
                lambda x: ['font-weight: bold' if h else '' for h in df['highlight']], axis=0
            )
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Columns found: " + ", ".join(actual_cols))
            st.info("ℹ️ Expected columns not found in view.")

        # --- Request New Club ---
        st.markdown("---")
        with st.expander("➕ Request New Club"):
            # Associations dropdown
            cursor.execute("SELECT id, association_name FROM xabuteo.public.associations ORDER BY association_name")
            assoc_data = cursor.fetchall()
            assoc_options = {name: id for id, name in assoc_data}
            assoc_name = st.selectbox("Select Association", list(assoc_options.keys()))

            # Clubs dropdown (filtered)
            if assoc_name:
                assoc_id = assoc_options[assoc_name]
                cursor.execute("""
                    SELECT id, club_name FROM xabuteo.public.clubs
                    WHERE association_id = %s
                    ORDER BY club_name
                """, (assoc_id,))
                club_data = cursor.fetchall()
                club_options = {name: id for id, name in club_data}

                club_name = st.selectbox("Select Club", list(club_options.keys()))
                valid_from = st.date_input("Valid From", date.today())
                valid_to = st.date_input("Valid To", date.today())

                if st.button("Submit Club Request"):
                    club_id = club_options[club_name]
                    try:
                        cursor.execute("""
                            INSERT INTO XABUTEO.PUBLIC.PLAYER_CLUB (PLAYER_ID, CLUB_ID, VALID_FROM, VALID_TO)
                            VALUES (%s, %s, %s, %s)
                        """, (player_id, club_id, valid_from, valid_to))
                        conn.commit()
                        st.success("✅ Club request submitted successfully.")
                    except Exception as e:
                        st.error(f"❌ Failed to submit request: {e}")

    except Exception as e:
        st.error(f"❌ Error loading clubs: {e}")
    finally:
        cursor.close()
        conn.close()
show()      
