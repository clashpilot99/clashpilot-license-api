import os
import smtplib
import uuid
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # للسماح بالطلبات من موقعك

SENDER_EMAIL = "info@bimora.org"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

@app.route("/")
def index():
    return "Clash Pilot License API is running."

@app.route("/generate-license", methods=["POST"])
def generate_license():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        company = data.get("company")
        position = data.get("position")

        if not all([name, email, company, position]):
            return jsonify({"error": "Missing required fields."}), 400

        # توليد مفتاح ترخيص
        license_key = uuid.uuid4().hex[:20]

        # إعداد الرسالة
        subject = "Your Clash Pilot License Key"
        body = f"""
Hello {name},

Thank you for requesting a trial license for Clash Pilot.

Here is your license key: {license_key}

Please enter this key in the Clash Pilot plugin inside Revit.

Best regards,  
BIMora Team
"""
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = email

        # إرسال الإيميل
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())

        return jsonify({"license_key": license_key})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # المنفذ المناسب لـ Render
    app.run(host="0.0.0.0", port=port)
