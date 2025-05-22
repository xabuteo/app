import os
import snowflake.connector
import bcrypt
import smtplib
from email.message import EmailMessage

SNOWFLAKE_CONFIG = {
    'user': os.environ.get('user'),
    'password': os.environ.get('password'),
    'account': os.environ.get('account'),
    'warehouse': os.environ.get('warehouse'),
    'database': os.environ.get('database'),
    'schema': os.environ.get('schema')
}

def send_email(to_email, subject, message):
    msg = EmailMessage()
    msg.set_content(message)
    msg["Subject"] = subject
    msg["From"] = "no-reply@xabuteo.com"  # Replace with your sender
    msg["To"] = to_email

    # Example using Gmail SMTP (replace with your SMTP server config)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("your-email@gmail.com", "your-password")  # Secure this properly!
        smtp.send_message(msg)

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_CONFIG['user'],
        password=SNOWFLAKE_CONFIG['password'],
        account=SNOWFLAKE_CONFIG['account'],
        warehouse=SNOWFLAKE_CONFIG['warehouse'],
        database=SNOWFLAKE_CONFIG['database'],
        schema=SNOWFLAKE_CONFIG['schema']
    )

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
