from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# قاعدة بيانات رخص مؤقتة - يمكن لاحقًا ربطها بقاعدة بيانات فعلية
licenses = {
    "ABC123-DEMO-MACHINE": {
        "company": "Demo Co",
        "start_date": "2025-05-01",
        "valid_days": 14
    }
}

@app.route("/")
def index():
    return "Clash Pilot License API - Online ✅"

@app.route("/validate", methods=["POST"])
def validate_license():
    data = request.json
    machine_id = data.get("machine_id")

    if not machine_id or machine_id not in licenses:
        return jsonify({"status": "invalid", "message": "License not found"}), 403

    lic = licenses[machine_id]
    start = datetime.strptime(lic["start_date"], "%Y-%m-%d")
    days_used = (datetime.now() - start).days

    if days_used > lic["valid_days"]:
        return jsonify({"status": "expired", "message": "License expired"}), 403

    return jsonify({
        "status": "valid",
        "company": lic["company"],
        "days_left": lic["valid_days"] - days_used
    })