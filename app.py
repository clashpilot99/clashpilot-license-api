from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)  # يسمح بالاتصال من أي مصدر (مثل موقعك)

@app.route('/generate-license', methods=['POST'])
def generate_license():
    data = request.json

    # استخراج البيانات من JSON
    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    position = data.get('position')

    # التحقق من أن جميع الحقول موجودة
    if not all([name, email, company, position]):
        return jsonify({"error": "All fields (name, email, company, position) are required."}), 400

    # توليد مفتاح ترخيص فريد (UUID)
    license_key = str(uuid.uuid4()).upper()

    # (اختياري) سجل البيانات - مثال: طباعتها في الـ Console
    print(f"New License Request:\nName: {name}\nEmail: {email}\nCompany: {company}\nPosition: {position}\nLicense: {license_key}")

    # إرسال المفتاح للعميل
    return jsonify({"license_key": license_key})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
