# --- Update Profile Form ---
with st.expander("✏️ Update Profile"):
    with st.form("update_profile_form"):
        new_first = st.text_input("First Name", db_first)
        new_last = st.text_input("Last Name", db_last)
        new_dob = st.date_input("Date of Birth", dob)
        new_gender = st.selectbox("Gender", ["M", "F", "Other"], index=["M", "F", "Other"].index(gender))

        # Email shown but disabled since it's tied to login
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
                        updated_at = CURRENT_TIMESTAMP,
                        updated_by = %s
                    WHERE email = %s
                """, (
                    new_first, new_last, new_dob.strftime('%Y-%m-%d'),
                    new_gender, current_email, current_email
                ))
                conn.commit()

                # Update session state (name fields only)
                st.session_state["user_info"]["given_name"] = new_first
                st.session_state["user_info"]["family_name"] = new_last

                st.success("✅ Profile updated successfully. Please refresh the page.")
            except Exception as e:
                st.error(f"❌ Failed to update profile: {e}")
