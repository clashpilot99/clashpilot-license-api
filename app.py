from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import string
import smtplib
import os
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

SENDER_EMAIL = "info@bimora.org"
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def generate_license_key():
    return ''.join(random.choices(string.hexdigits.lower(), k=16))

def send_email(receiver_email, license_key):
    msg = MIMEText(f"Your Clash Pilot License Key: {license_key}")
    msg['Subject'] = 'Clash Pilot License Key'
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    with smtplib.SMTP('smtp.hostinger.com', 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

@app.route('/generate-license', methods=['POST'])
def generate_license():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    purpose = data.get('purpose')

    if not all([name, email, company, purpose]):
        return jsonify({'error': 'Missing required fields.'}), 400

    license_key = generate_license_key()

    try:
        send_email(email, license_key)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'license_key': license_key})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
