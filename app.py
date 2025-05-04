from flask import Flask, request, jsonify
from flask_cors import CORS
import secrets
import smtplib
from email.mime.text import MIMEText
from os import environ

app = Flask(__name__)
CORS(app)

# إعداد البريد
EMAIL_ADDRESS = "info@bimora.org"
EMAIL_PASSWORD = environ.get("EMAIL_PASSWORD")  # من Environment Variables في Render

@app.route("/generate-license", methods=["POST"])
def generate_license():
    try:
        data = request.get_json()
        full_name = data.get("full_name")
        email = data.get("email")
        company = data.get("company")
        position = data.get("position")

        if not all([full_name, email, company, position]):
            return jsonify({"error": "Missing fields"}), 400

        # توليد المفتاح العشوائي
        license_key = secrets.token_hex(8)

        # إعداد رسالة الإيميل
        subject = "Your Clash Pilot License Key"
        body = f"""
Hello {full_name},

Thank you for trying Clash Pilot!

🔐 Your license key is:
{license_key}

Best regards,  
Clash Pilot Team  
www.bimora.org
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        # إرسال الإيميل
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        return jsonify({"license_key": license_key})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ دعم Render - فتح المنفذ المناسب
if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
