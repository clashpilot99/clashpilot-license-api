import os
import smtplib
import string
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

def generate_license_key(length=16):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def send_email(recipient_email, license_key, full_name, company_name, position):
    sender_email = "info@bimora.org"
    sender_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = "smtp.hostinger.com"
    smtp_port = 465

    subject = "Your Clash Pilot License Key"
    body = f"""
    Hello {full_name},

    Thank you for requesting a license key for Clash Pilot.
    
    🎫 Your License Key: {license_key}

    📌 Info Provided:
    - Company: {company_name}
    - Position: {position}
    - Email: {recipient_email}

    Please keep this key safe and use it in the plugin settings.

    Regards,
    Clash Pilot Team
    """

    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = recipient_email

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

@app.route("/generate-license", methods=["POST"])
def generate_license():
    data = request.get_json()
    required_fields = ['fullName', 'email', 'companyName', 'position']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"error": "Missing required fields."}), 400

    try:
        license_key = generate_license_key()
        send_email(
            recipient_email=data["email"],
            license_key=license_key,
            full_name=data["fullName"],
            company_name=data["companyName"],
            position=data["position"]
        )
        return jsonify({"license_key": license_key})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
