# --- START OF app.py (v2.2 - Added import sys) ---
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import string
import smtplib
import os
from email.mime.text import MIMEText
import psycopg2 # For PostgreSQL interaction
from psycopg2 import sql # For safe SQL query construction
from datetime import datetime, timedelta, timezone # For timestamps
from urllib.parse import urlparse # For parsing DATABASE_URL
import traceback # For detailed error logging
from dotenv import load_dotenv # Optional: for local development to load .env file
import sys # <-- ADDED IMPORT SYS

# --- Load environment variables from .env file for local development ---
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # Allow requests from your frontend

# --- Configuration from Environment Variables ---
SENDER_EMAIL = "info@bimora.org"
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")
DATABASE_URL = os.environ.get("DATABASE_URL")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

# --- Helper Functions ---

def print_error(*args, **kwargs):
    """Prints messages to stderr for logging purposes."""
    # Now sys is defined
    print(*args, file=sys.stderr, **kwargs)

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        print_error("FATAL: DATABASE_URL environment variable not set.")
        raise ConnectionError("Database configuration is missing.")
    try:
        result = urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn
    except Exception as e:
        print_error(f"Error connecting to database: {e}")
        raise ConnectionError(f"Could not connect to the database: {e}")

def create_licenses_table_if_not_exists():
    """Creates the licenses table in the database if it doesn't already exist."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                license_key VARCHAR(36) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                company VARCHAR(255),
                purpose TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                activated_machine_id VARCHAR(255) NULL,
                last_validated_at TIMESTAMP WITH TIME ZONE NULL,
                expires_at TIMESTAMP WITH TIME ZONE NULL
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses (license_key);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses (email);")
        conn.commit()
        cur.close()
        print_error("Ensured 'licenses' table exists.")
    except Exception as e:
        print_error(f"Error creating/checking licenses table: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

def generate_license_key():
    """Generates a unique license key (UUID4)."""
    import uuid
    return str(uuid.uuid4())

def send_email(receiver_email, license_key):
    """Sends the license key via email."""
    if not SENDER_PASSWORD:
        print_error("EMAIL_PASSWORD environment variable not set. Cannot send email.")
        raise ValueError("Email configuration incomplete on server.")
    if not SENDER_EMAIL:
         print_error("SENDER_EMAIL not configured. Cannot send email.")
         raise ValueError("Sender email configuration incomplete.")

    body = f"""Hi there,

Thank you for your interest in Clash Pilot!

Your License Key is: {license_key}

Please keep this key safe and use it to activate the add-in within Revit.

If you have any questions, feel free to reply to this email.

Best regards,
The BIMORA Team
info@bimora.org
"""
    msg = MIMEText(body)
    msg['Subject'] = 'Your Clash Pilot License Key'
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print_error(f"License key sent successfully to {receiver_email}")
    except smtplib.SMTPAuthenticationError as e:
        print_error(f"SMTP Authentication Error: {e}. Check SENDER_EMAIL ({SENDER_EMAIL}) and EMAIL_PASSWORD configuration.")
        raise ConnectionError("Failed to authenticate with email server.")
    except Exception as e:
        print_error(f"Error sending email to {receiver_email}: {e}")
        print_error(traceback.format_exc())
        raise ConnectionError(f"Failed to send email: {e}")

# --- API Endpoints ---

@app.route('/generate-license', methods=['POST'])
def generate_license():
    """Endpoint to generate, store, and email a new license key."""
    data = request.get_json()
    if not data: return jsonify({'error': 'Invalid JSON data received.'}), 400

    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    purpose = data.get('purpose')

    if not name or not email: return jsonify({'error': 'Missing required fields (name, email).'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT license_key FROM licenses WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            existing_key = existing[0]
            print_error(f"Email {email} already exists with key {existing_key}. Resending.")
            try:
                send_email(email, existing_key)
                return jsonify({'message': f'License key for {email} already existed and has been re-sent.'}), 200
            except Exception as send_err:
                 return jsonify({'error': f'Email already exists, but failed to resend key: {send_err}'}), 500
            finally:
                 cur.close()
                 conn.close()

        while True:
            license_key = generate_license_key()
            cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (license_key,))
            if cur.fetchone() is None: break

        expiration_date = None # Set expiration logic here if needed

        insert_query = sql.SQL("""
            INSERT INTO licenses (license_key, name, email, company, purpose, is_active, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """)
        cur.execute(insert_query, (license_key, name, email, company, purpose, True, expiration_date))
        conn.commit()
        print_error(f"License key {license_key} generated and stored for {email}.")

        send_email(email, license_key)

        return jsonify({'message': 'License key generated and sent successfully.'}), 201

    except psycopg2.Error as db_err:
        print_error(f"Database Error in /generate-license: {db_err}"); print_error(traceback.format_exc())
        if conn: conn.rollback()
        return jsonify({'error': f'Database operation failed: {db_err}'}), 500
    except ConnectionError as conn_err:
         print_error(f"Connection Error in /generate-license: {conn_err}"); print_error(traceback.format_exc())
         if conn: conn.rollback()
         return jsonify({'error': str(conn_err)}), 503
    except Exception as e:
        print_error(f"General Error in /generate-license: {e}"); print_error(traceback.format_exc())
        if conn: conn.rollback()
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500
    finally:
        # Ensure cursor is closed before connection
        if 'cur' in locals() and cur and not cur.closed: cur.close()
        if conn: conn.close()


@app.route('/validate-license', methods=['POST'])
def validate_license():
    """Endpoint to validate a license key against a machine ID."""
    data = request.get_json()
    if not data: return jsonify({'status': 'invalid', 'reason': 'No data received.'}), 400

    license_key = data.get('license_key')
    machine_id = data.get('machine_id')

    if not license_key or not machine_id:
        return jsonify({'status': 'invalid', 'reason': 'Missing license_key or machine_id.'}), 400

    conn = None
    cur = None # Define cursor outside try
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        select_query = """
            SELECT id, is_active, activated_machine_id, expires_at
            FROM licenses
            WHERE license_key = %s;
        """
        cur.execute(select_query, (license_key,))
        result_row = cur.fetchone()

        if result_row is None:
            return jsonify({'status': 'invalid', 'reason': 'License key not found.'}), 404

        license_id, is_active, activated_machine, expires_at = result_row

        if not is_active:
            return jsonify({'status': 'invalid', 'reason': 'License key is inactive.'}), 403

        if expires_at is not None and datetime.now(timezone.utc) > expires_at:
            return jsonify({'status': 'expired', 'reason': 'License key has expired.'}), 403

        current_time = datetime.now(timezone.utc)
        if activated_machine is None:
            update_activation_query = """
                UPDATE licenses SET activated_machine_id = %s, last_validated_at = %s WHERE id = %s;
            """
            cur.execute(update_activation_query, (machine_id, current_time, license_id))
            conn.commit()
            print_error(f"License key {license_key} activated for machine {machine_id}")
            return jsonify({'status': 'valid', 'message': 'License activated successfully.'}), 200

        elif activated_machine == machine_id:
            update_last_validated_query = "UPDATE licenses SET last_validated_at = %s WHERE id = %s;"
            cur.execute(update_last_validated_query, (current_time, license_id))
            conn.commit()
            print_error(f"License key {license_key} validated successfully for machine {machine_id}")
            return jsonify({'status': 'valid'}), 200
        else:
            print_error(f"License key {license_key} validation failed. Already activated on machine '{activated_machine}', attempted by '{machine_id}'")
            return jsonify({'status': 'invalid', 'reason': 'License key already activated on another machine.'}), 403

    except psycopg2.Error as db_err:
        print_error(f"Database Error in /validate-license: {db_err}"); print_error(traceback.format_exc())
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'reason': 'License server database error.'}), 500
    except ConnectionError as conn_err:
         print_error(f"Connection Error in /validate-license: {conn_err}"); print_error(traceback.format_exc())
         return jsonify({'status': 'error', 'reason': 'Could not connect to license server.'}), 503
    except Exception as e:
        print_error(f"General Error in /validate-license: {e}"); print_error(traceback.format_exc())
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'reason': 'An unexpected error occurred on the license server.'}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

# --- Entry Point & Setup ---
if __name__ == '__main__':
    print_error("Starting license API...")
    try:
        create_licenses_table_if_not_exists()
        print_error("License API setup complete. Ready for Gunicorn or local run.")
    except ConnectionError as start_conn_err:
        print_error(f"FATAL: Could not connect to database on startup: {start_conn_err}")
    except Exception as start_err:
        print_error(f"FATAL: Error during initial table setup: {start_err}"); print_error(traceback.format_exc())

    # For local testing ONLY: uncomment the line below and run 'python app.py'
    # app.run(host='0.0.0.0', port=10000, debug=True)

# --- END OF app.py ---
