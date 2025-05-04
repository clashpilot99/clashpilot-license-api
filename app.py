from flask import Flask, request, jsonify
import uuid
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

SENDER_EMAIL = "info@bimora.org"
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Secure method
SMTP_SERVER = "smtp.hostinger.com"
SMTP_PORT = 587

@app.route("/generate-license", methods=["POST"])
def generate_license():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    company = data.get("company")
    position = data.get("position")

    license_key = str(uuid.uuid4())

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎉 Your Clash Pilot License Key"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email

        html_content = f"""<html>
<body>
    <h2>Hi {name},</h2>
    <p>Thanks for requesting your Clash Pilot license!</p>
    <p><b>Your license key:</b></p>
    <p style='font-size: 20px; font-weight: bold; color: #007bff;'>{license_key}</p>
    <hr>
    <p><b>Company:</b> {company}<br>
    <b>Position:</b> {position}</p>
    <p style='color: gray;'>Powered by BIMora - Clash Pilot</p>
</body>
</html>
"""

        part = MIMEText(html_content, "html")
        msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())

        return jsonify({"license_key": license_key}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
