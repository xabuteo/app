import streamlit as st
from utils import get_db_connectionX

conn = get_db_connectionX()
if conn:
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    st.write("Tables:", tables)
    cursor.close()
    conn.close()
