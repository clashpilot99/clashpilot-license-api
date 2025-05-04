from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.message import EmailMessage
import secrets
import os

app = Flask(__name__)
CORS(app)

# إعدادات بريد Outlook / Microsoft 365
EMAIL_ADDRESS = "info@bimora.org"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # ضع كلمة المرور كمتغير بيئة في Render
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587  # Outlook يفضل STARTTLS على هذا البورت

@app.route('/generate-license', methods=['POST'])
def generate_license():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    position = data.get('position')

    # تحقق من المدخلات
    if not all([name, email, company, position]):
        return jsonify({"error": "Missing required fields."}), 400

    # توليد مفتاح الرخصة العشوائي
    license_key = secrets.token_hex(8)

    # إنشاء رسالة البريد
    msg = EmailMessage()
    msg['Subject'] = "Your Clash Pilot License Key"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email
    msg.set_content(f"""
Hello {name},

✅ Thank you for requesting a free Clash Pilot license.

🔐 Your License Key: {license_key}

Company: {company}
Position: {position}

Please copy and paste this license key inside the Clash Pilot Revit plugin when asked.

Best regards,  
BIMora Team
info@bimora.org
""")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Start TLS encryption
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return jsonify({"license_key": license_key}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
