import streamlit as st
import pandas as pd
from utils import get_snowflake_connection, ensure_profile_complete
from datetime import date

def show():
    st.title("🏟️ My Clubs")

    ensure_profile_complete()

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Get Player ID for logged-in user
        cursor.execute(
            "SELECT ID FROM XABUTEO.PUBLIC.REGISTRATIONS WHERE EMAIL = %s", 
            (st.user.email,)
        )
        player_row = cursor.fetchone()
        if not player_row:
            st.error("❌ Could not find player ID.")
            return
        player_id = player_row[0]

        # --- Display PLAYER_CLUB_V view ---
        cursor.execute(
            "SELECT * FROM XABUTEO.PUBLIC.PLAYER_CLUB_V WHERE EMAIL = %s", 
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

        # --- Request New Club ---
        st.markdown("---")
        with st.expander("➕ Request New Club"):
            # Associations dropdown
            cursor.execute("""
                SELECT id, association_name 
                FROM xabuteo.public.associations 
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
                        FROM xabuteo.public.clubs 
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
                                    INSERT INTO XABUTEO.PUBLIC.PLAYER_CLUB 
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

    except Exception as e:
        st.error(f"❌ Error loading clubs: {e}")
    finally:
        cursor.close()
        conn.close()

# Required for multipage apps
if __name__ == "__main__":
    show()
