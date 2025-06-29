import streamlit as st
import datetime
from utils import get_snowflake_connection
from sidebar_utils import render_sidebar_widgets

today = datetime.date.today()
hundred_years_ago = today.replace(year=today.year - 100)

def get_initials(first, last):
    if not first or not last:
        return "?"
    return f"{first[0].upper()}{last[0].upper()}"

def show():
    st.title("🙋 My Profile")

    if not st.user.is_logged_in:
        st.warning("🔒 Please log in to view your profile.")
        return

    current_email = st.user.email

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

        first_name, last_name, dob, gender, email = row
        initials = get_initials(first_name, last_name)

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

        # --- Profile table without headers ---
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

        profile_row("First Name", first_name)
        profile_row("Last Name", last_name)
        profile_row("Date of Birth", dob)
        profile_row("Gender", gender)
        profile_row("Email", email)

        # --- Update Profile Form ---
        with st.expander("✏️ Update Profile"):
            with st.form("update_profile_form", clear_on_submit=False):
                new_first = st.text_input("First Name", value=first_name)
                new_last = st.text_input("Last Name", value=last_name)
                new_dob = st.date_input(
                    "Date of Birth",
                    value=dob,
                    min_value=hundred_years_ago,
                    max_value=today
                )
                gender_options = ["M", "F", "Other"]
                index = gender_options.index(gender) if gender in gender_options else 0
                new_gender = st.selectbox("Gender", gender_options, index=index)

                submitted = st.form_submit_button("Update")

                if submitted:
                    if not new_first or not new_last or not new_dob or not new_gender:
                        st.error("⚠️ All fields are required.")
                    else:
                        try:
                            cursor.execute("""
                                UPDATE registrations
                                SET first_name = %s,
                                    last_name = %s,
                                    date_of_birth = %s,
                                    gender = %s,
                                    updated_at = CURRENT_TIMESTAMP(),
                                    updated_by = %s
                                WHERE email = %s
                            """, (
                                new_first,
                                new_last,
                                new_dob.strftime('%Y-%m-%d'),
                                new_gender,
                                current_email,  # updated_by
                                current_email
                            ))
                            conn.commit()
                            st.success("✅ Profile updated successfully. Please refresh the page.")
                        except Exception as e:
                            st.error(f"❌ Failed to update profile: {e}")

    except Exception as e:
        st.error(f"❌ Error retrieving profile: {e}")
    finally:
        cursor.close()
        conn.close()

show()
render_sidebar_widgets()
