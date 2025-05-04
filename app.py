from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

@app.route('/generate-license', methods=['POST'])
def generate_license():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    position = data.get('position')

    if not all([name, email, company, position]):
        return jsonify({'error': 'Missing data'}), 400

    license_key = uuid.uuid4().hex[:20]

    try:
        send_license_email(email, license_key)
        return jsonify({'license_key': license_key}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_license_email(receiver_email, license_key):
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASSWORD")

    message = MIMEText(f"Your Clash Pilot license key is: {license_key}")
    message['Subject'] = "Clash Pilot License Key"
    message['From'] = sender_email
    message['To'] = receiver_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.sendmail(sender_email, receiver_email, message.as_string())
