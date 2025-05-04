from flask import Flask, request, jsonify
import uuid
import json
import os
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # للسماح للـ HTML في موقعك بالتواصل مع هذا API

LICENSE_FILE = "licenses.json"

def load_licenses():
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            return json.load(f)
    return []

def save_licenses(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/generate-license", methods=["POST"])
def generate_license():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    country = data.get("country")
    company = data.get("company")

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    # توليد لايسنس
    license_key = f"TRIAL-{uuid.uuid4().hex[:12].upper()}"
    valid_until = (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d")

    # حفظه
    licenses = load_licenses()
    licenses.append({
        "name": name,
        "email": email,
        "country": country,
        "company": company,
        "license_key": license_key,
        "valid_until": valid_until
    })
    save_licenses(licenses)

    return jsonify({
        "status": "success",
        "license_key": license_key,
        "valid_until": valid_until
    })

@app.route("/", methods=["GET"])
def home():
    return "ClashPilot License API is running ✅"

if __name__ == "__main__":
    app.run(debug=True, port=5000)
