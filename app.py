from flask import Flask, request, jsonify
import hashlib
import os

app = Flask(__name__)

@app.route('/')
def home():
    return 'ClashPilot License API is running!'

@app.route('/generate-license', methods=['POST'])
def generate_license():
    try:
        data = request.get_json()
        email = data.get("email")
        if not email:
            return jsonify({"error": "Email is required."}), 400

        # Example: create a hashed license key from the email (simple logic for demo)
        raw = f"{email}-clashpilot-demo"
        license_key = hashlib.sha256(raw.encode()).hexdigest()[:20]  # Take first 20 characters

        return jsonify({"license_key": license_key})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
