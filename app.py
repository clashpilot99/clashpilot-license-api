# --- START OF app.py (v2.2 - Email+Key Validation & Activation Control) ---
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import string
import smtplib
import os
from email.mime.text import MIMEText
import psycopg2
from psycopg2 import sql
from datetime import datetime, timezone # timezone is important for expires_at comparison
from urllib.parse import urlparse
import traceback
from dotenv import load_dotenv
import sys
import uuid # Use UUID for license keys

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Configuration ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "info@bimora.org")
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")
DATABASE_URL = os.environ.get("DATABASE_URL")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

# --- Helper Functions (get_db_connection, create_licenses_table_if_not_exists, send_email - No change needed) ---
def print_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def get_db_connection():
    if not DATABASE_URL:
        print_error("FATAL: DATABASE_URL environment variable not set.")
        raise ConnectionError("Database configuration is missing.")
    try:
        result = urlparse(DATABASE_URL)
        conn = psycopg2.connect(dbname=result.path[1:], user=result.username, password=result.password, host=result.hostname, port=result.port)
        return conn
    except Exception as e:
        print_error(f"Error connecting to database: {e}")
        raise ConnectionError(f"Could not connect to the database: {e}")

def create_licenses_table_if_not_exists():
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
                is_active BOOLEAN DEFAULT TRUE, -- This flag allows manual activation/deactivation
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
    return str(uuid.uuid4()) # Use UUID

def send_email(receiver_email, license_key):
    if not SENDER_PASSWORD or not SENDER_EMAIL:
        print_error("Email configuration incomplete (SENDER_EMAIL or EMAIL_PASSWORD missing).")
        raise ValueError("Email configuration incomplete on server.")
    body = f"""Hi there,\n\nThank you for your interest in Clash Pilot!\n\nYour License Key is: {license_key}\n\nPlease use this key along with your email address ({receiver_email}) to activate the add-in within Revit.\n\nKeep this key safe.\n\nBest regards,\nThe BIMORA Team\n{SENDER_EMAIL}"""
    msg = MIMEText(body)
    msg['Subject'] = 'Your Clash Pilot License Key'
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print_error(f"License key sent successfully to {receiver_email}")
    except smtplib.SMTPAuthenticationError as e:
        print_error(f"SMTP Authentication Error: {e}. Check SENDER_EMAIL/EMAIL_PASSWORD."); raise ConnectionError("Failed to authenticate with email server.")
    except Exception as e:
        print_error(f"Error sending email to {receiver_email}: {e}\n{traceback.format_exc()}"); raise ConnectionError(f"Failed to send email: {e}")

# --- API Endpoints ---

@app.route('/generate-license', methods=['POST'])
def generate_license():
    # --- (No significant changes needed here from previous version - it still stores by email) ---
    data = request.get_json(); # ... (rest of the generate_license function remains the same) ...
    if not data: return jsonify({'error': 'Invalid JSON data received.'}), 400
    name = data.get('name'); email = data.get('email'); company = data.get('company'); purpose = data.get('purpose')
    if not name or not email: return jsonify({'error': 'Missing required fields (name, email).'}), 400
    conn = None; cur = None
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute("SELECT license_key FROM licenses WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            existing_key = existing[0]
            print_error(f"Email {email} already exists with key {existing_key}. Resending.")
            try: send_email(email, existing_key); return jsonify({'message': f'License key for {email} already existed and has been re-sent.'}), 200
            except Exception as send_err: return jsonify({'error': f'Email already exists, but failed to resend key: {send_err}'}), 500
            finally: cur.close(); conn.close() # Close connection after resend attempt
        while True:
            license_key = generate_license_key()
            cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (license_key,))
            if cur.fetchone() is None: break
        expiration_date = None
        insert_query = sql.SQL("INSERT INTO licenses (license_key, name, email, company, purpose, is_active, expires_at) VALUES (%s, %s, %s, %s, %s, %s, %s);")
        cur.execute(insert_query, (license_key, name, email, company, purpose, True, expiration_date))
        conn.commit()
        print_error(f"License key {license_key} generated and stored for {email}.")
        send_email(email, license_key)
        return jsonify({'message': 'License key generated and sent successfully.'}), 201
    except psycopg2.Error as db_err: print_error(f"Database Error in /generate-license: {db_err}\n{traceback.format_exc()}"); conn.rollback(); return jsonify({'error': f'Database operation failed: {db_err}'}), 500
    except ConnectionError as conn_err: print_error(f"Connection Error in /generate-license: {conn_err}\n{traceback.format_exc()}"); return jsonify({'error': str(conn_err)}), 503
    except Exception as e: print_error(f"General Error in /generate-license: {e}\n{traceback.format_exc()}"); conn.rollback(); return jsonify({'error': f'An unexpected error occurred: {e}'}), 500
    finally:
        if cur and not cur.closed: cur.close()
        if conn and not conn.closed: conn.close()


@app.route('/validate-license', methods=['POST'])
def validate_license():
    """Endpoint to validate a license key AND user email against a machine ID."""
    data = request.get_json()
    if not data: return jsonify({'status': 'invalid', 'reason': 'No data received.'}), 400

    license_key = data.get('license_key')
    machine_id = data.get('machine_id')
    user_email = data.get('user_email') # *** Get user email from request ***

    if not license_key or not machine_id or not user_email:
        return jsonify({'status': 'invalid', 'reason': 'Missing license_key, machine_id, or user_email.'}), 400

    # Optional: Basic email format validation
    # import re
    # if not re.match(r"[^@]+@[^@]+\.[^@]+", user_email):
    #     return jsonify({'status': 'invalid', 'reason': 'Invalid email format.'}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # *** Query using BOTH license key AND email ***
        select_query = """
            SELECT id, is_active, activated_machine_id, expires_at
            FROM licenses
            WHERE license_key = %s AND email = %s;
        """
        cur.execute(select_query, (license_key, user_email)) # Pass both key and email
        result_row = cur.fetchone()

        if result_row is None:
            # Key/Email combination not found
            return jsonify({'status': 'invalid', 'reason': 'License key not found or does not match the provided email.'}), 404

        license_id, is_active, activated_machine, expires_at = result_row

        # *** Check is_active flag ***
        if not is_active:
            return jsonify({'status': 'invalid', 'reason': 'License key has been deactivated by the administrator.'}), 403

        # Check expiration (optional)
        if expires_at is not None and datetime.now(timezone.utc) > expires_at:
            return jsonify({'status': 'expired', 'reason': 'License key has expired.'}), 403

        # Check machine activation
        current_time = datetime.now(timezone.utc)
        if activated_machine is None:
            # First activation for this key/email combo
            update_activation_query = "UPDATE licenses SET activated_machine_id = %s, last_validated_at = %s WHERE id = %s;"
            cur.execute(update_activation_query, (machine_id, current_time, license_id))
            conn.commit()
            print_error(f"License key {license_key} (Email: {user_email}) activated for machine {machine_id}")
            return jsonify({'status': 'valid', 'message': 'License activated successfully.'}), 200

        elif activated_machine == machine_id:
            # Correct machine
            update_last_validated_query = "UPDATE licenses SET last_validated_at = %s WHERE id = %s;"
            cur.execute(update_last_validated_query, (current_time, license_id))
            conn.commit()
            print_error(f"License key {license_key} (Email: {user_email}) validated successfully for machine {machine_id}")
            return jsonify({'status': 'valid'}), 200
        else:
            # Activated on a different machine
            print_error(f"License key {license_key} (Email: {user_email}) validation failed. Activated on '{activated_machine}', attempted by '{machine_id}'")
            return jsonify({'status': 'invalid', 'reason': 'License key already activated on another machine.'}), 403

    # ... (Error handling remains the same) ...
    except psycopg2.Error as db_err: print_error(f"Database Error in /validate-license: {db_err}\n{traceback.format_exc()}"); conn.rollback(); return jsonify({'status': 'error', 'reason': 'License server database error.'}), 500
    except ConnectionError as conn_err: print_error(f"Connection Error in /validate-license: {conn_err}\n{traceback.format_exc()}"); return jsonify({'status': 'error', 'reason': 'Could not connect to license server.'}), 503
    except Exception as e: print_error(f"General Error in /validate-license: {e}\n{traceback.format_exc()}"); conn.rollback(); return jsonify({'status': 'error', 'reason': 'An unexpected error occurred on the license server.'}), 500
    finally:
        if cur and not cur.closed: cur.close()
        if conn and not conn.closed: conn.close()


# --- Entry Point & Setup ---
if __name__ == '__main__':
    print_error("Starting license API...")
    try:
        create_licenses_table_if_not_exists()
        print_error("License API setup complete. Ready for Gunicorn or local run.")
    except ConnectionError as start_conn_err: print_error(f"FATAL: Could not connect to database on startup: {start_conn_err}")
    except Exception as start_err: print_error(f"FATAL: Error during initial table setup: {start_err}\n{traceback.format_exc()}")
    # app.run(host='0.0.0.0', port=10000, debug=True) # For local testing

# --- END OF app.py ---
