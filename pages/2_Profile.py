import streamlit as st
import pandas as pd
from utils import get_snowflake_connection

def get_initials(first, last):
    return f"{first[0].upper()}{last[0].upper()}" if first and last else "?"

def show():
    st.set_page_config(page_title="My Profile")
    st.title("🙋 My Profile")

    # Auth0 access control
    if "user_info" not in st.session_state:
        st.warning("🔐 Please log in to view your profile.")
        st.stop()

    user_info = st.session_state["user_info"]
    current_email = user_info.get("email", "")
    first_name = user_info.get("given_name", "")
    last_name = user_info.get("family_name", "")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT first_name, last_name, date_of_birth, gender, email
            FROM registrations
            WHERE email = %s
        """, (current_email,))
        row = cursor.fetchone()

        if not row:
            st.error("⚠️ No profile found for this user.")
            return

        db_first, db_last, dob, gender, email = row
        initials = get_initials(db_first, db_last)

        # --- Avatar ---
        st.markdown(
            f"""
            <div style="text-align: center;">
                <div style="
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    background-color: #3dc2d4;
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 36px;
                    margin: 10px auto 20px auto;
                ">{initials}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- Profile table ---
        st.markdown("""
        <style>
        .profile-row { display: flex; margin-bottom: 0.5rem; }
        .profile-label { width: 140px; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

        def profile_row(label, value):
            st.markdown(
                f'<div class="profile-row"><div class="profile-label">{label}:</div><div>{value}</div></div>',
                unsafe_allow_html=True
            )

        profile_row("First Name", db_first)
        profile_row("Last Name", db_last)
        profile_row("Date of Birth", dob)
        profile_row("Gender", gender)
        profile_row("Email", email)

        # --- Update Profile Form ---
        with st.expander("✏️ Update Profile"):
            with st.form("update_profile_form"):
                new_first = st.text_input("First Name", first_name)
                new_last = st.text_input("Last Name", last_name)
                new_dob = st.date_input("Date of Birth", dob)
        
                gender_options = ["M", "F", "Other"]
                default_gender = gender if gender in gender_options else "Other"
                new_gender = st.selectbox("Gender", gender_options, index=gender_options.index(default_gender))
        
                # Optional: disable email change field
                st.text_input("Email", email, disabled=True)
        
                submitted = st.form_submit_button("Update")
                if submitted:
                    try:
                        cursor.execute("""
                            UPDATE registrations
                            SET first_name = %s,
                                last_name = %s,
                                date_of_birth = %s,
                                gender = %s,
                                email = %s,
                                updated_at = CURRENT_TIMESTAMP(),
                                updated_by = %s
                            WHERE email = %s
                        """, (
                            new_first,
                            new_last,
                            new_dob.strftime('%Y-%m-%d'),  # 👈 convert date to string
                            new_gender,
                            new_email,
                            st.session_state.get("user_email", ""),  # updated_by
                            current_email
                        ))
                        conn.commit()
                        st.session_state["user_email"] = new_email
                        st.success("✅ Profile updated successfully. Please refresh the page.")
                    except Exception as e:
                        st.error(f"❌ Failed to update profile: {e}")

    except Exception as e:
        st.error(f"❌ Error retrieving profile: {e}")
    finally:
        cursor.close()
        conn.close()

show()
