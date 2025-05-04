from flask import Flask, request, jsonify
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# إعدادات البريد الخاص بك (Hostinger SMTP)
SMTP_SERVER = 'smtp.hostinger.com'
SMTP_PORT = 587
SMTP_USER = 'info@bimora.org'
SMTP_PASSWORD = 'ضع_كلمة_المرور_هنا'  # ⚠️ تأكد أنها آمنة

@app.route('/generate-license', methods=['POST'])
def generate_license():
    data = request.form if request.form else request.json

    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    position = data.get('position')

    if not all([name, email, company, position]):
        return jsonify({"error": "Missing required fields"}), 400

    # توليد مفتاح الترخيص
    license_key = str(uuid.uuid4())

    # إعداد البريد
    subject = "Your Clash Pilot License Key"
    body = f"""
Hello {name},

Thanks for requesting a trial license for Clash Pilot.

🔑 Your License Key: {license_key}

Company: {company}
Position: {position}

You can now paste this license key in the plugin to activate the demo mode.

Regards,  
BIMora Team
"""

    # إرسال البريد
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        return jsonify({"error": f"Email send failed: {str(e)}"}), 500

    # الاستجابة النهائية
    return jsonify({"license_key": license_key})
