from flask import Flask, request, jsonify
from flask_cors import CORS
import secrets
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)
CORS(app)

EMAIL_ADDRESS = os.environ.get("EMAIL_USER", "info@bimora.org")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

@app.route('/generate-license', methods=['POST'])
def generate_license():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        company = data.get('company')
        position = data.get('position')

        if not all([name, email, company, position]):
            return jsonify({"error": "Missing required fields"}), 400

        license_key = secrets.token_hex(8)

        msg = EmailMessage()
        msg['Subject'] = "Your Clash Pilot License Key"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg.set_content(f"""Hello {name},

Thank you for requesting a Clash Pilot license.

🔐 Your License Key: {license_key}

Company: {company}
Position: {position}

Use this key to activate your Clash Pilot plugin in Revit.

Best regards,
Clash Pilot Team - BIMora
""")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"license_key": license_key})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
