# --- START OF app.py (v2 - Database Integration) ---
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import string
import smtplib
import os
from email.mime.text import MIMEText
import psycopg2 # <-- استيراد مكتبة PostgreSQL
from psycopg2 import sql # <-- لاستعلامات SQL الآمنة
from datetime import datetime, timedelta # <-- لاستخدام التواريخ (لتاريخ الإنشاء وانتهاء الصلاحية المحتمل)
from urllib.parse import urlparse # <-- لتحليل رابط قاعدة البيانات

app = Flask(__name__)
CORS(app) # السماح بالطلبات من مصادر مختلفة (مثل صفحة HTML)

# --- إعدادات البريد الإلكتروني وقاعدة البيانات ---
SENDER_EMAIL = "info@bimora.org"
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD") # من متغيرات البيئة في Render

# --- هام: الحصول على رابط قاعدة البيانات من متغيرات البيئة ---
# سيتم تعيين هذا المتغير في لوحة تحكم Render باستخدام Internal Connection String
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- وظائف مساعدة ---

def get_db_connection():
    """إنشاء اتصال بقاعدة بيانات PostgreSQL."""
    try:
        # تحليل DATABASE_URL للحصول على المكونات
        result = urlparse(DATABASE_URL)
        username = result.username
        password = result.password
        database = result.path[1:] # إزالة الـ / من البداية
        hostname = result.hostname
        port = result.port

        conn = psycopg2.connect(
            dbname=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        return conn
    except Exception as e:
        print_error(f"Error connecting to database: {e}")
        # يمكنك هنا إما إرجاع None أو إثارة الخطأ للسماح للنقاط النهائية بمعالجته
        raise ConnectionError(f"Could not connect to the database: {e}")

def create_licenses_table_if_not_exists():
    """إنشاء جدول التراخيص إذا لم يكن موجودًا."""
    conn = None # تأكد من تعريف conn قبل try
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                license_key VARCHAR(16) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                company VARCHAR(255),
                purpose TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                activated_machine_id VARCHAR(255) NULL, -- لتتبع أول جهاز تم التفعيل عليه
                last_validated_at TIMESTAMP NULL,
                expires_at TIMESTAMP NULL -- يمكنك إضافة تاريخ انتهاء هنا لاحقًا
            );
        """)
        conn.commit()
        cur.close()
        print_error("Ensured 'licenses' table exists.")
    except Exception as e:
        print_error(f"Error creating/checking licenses table: {e}")
    finally:
        if conn:
            conn.close()

def generate_license_key(length=16):
    """توليد مفتاح ترخيص سداسي عشري فريد."""
    # يمكن استخدام UUID هنا لمزيد من الفرادة:
    # import uuid
    # return str(uuid.uuid4())
    # ولكن لنلتزم بـ 16 حرف سداسي عشري الآن
    return ''.join(random.choices(string.hexdigits.lower(), k=length))

def send_email(receiver_email, license_key):
    """إرسال البريد الإلكتروني بمفتاح الترخيص."""
    if not SENDER_PASSWORD:
        print_error("EMAIL_PASSWORD environment variable not set. Cannot send email.")
        raise ValueError("Email configuration incomplete on server.")

    msg = MIMEText(f"Thank you for your interest in Clash Pilot!\n\nYour License Key: {license_key}\n\nPlease keep this key safe.\n\nBest regards,\nThe BIMORA Team")
    msg['Subject'] = 'Your Clash Pilot License Key'
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP('smtp.hostinger.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print_error(f"License key sent successfully to {receiver_email}")
    except smtplib.SMTPAuthenticationError as e:
        print_error(f"SMTP Authentication Error: {e}. Check EMAIL_PASSWORD.")
        raise ConnectionError("Failed to authenticate with email server.")
    except Exception as e:
        print_error(f"Error sending email to {receiver_email}: {e}")
        raise ConnectionError(f"Failed to send email: {e}")

# --- نقاط نهاية الـ API ---

@app.route('/generate-license', methods=['POST'])
def generate_license():
    """نقطة نهاية لتوليد وتخزين وإرسال مفتاح ترخيص جديد."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON data received.'}), 400

    name = data.get('name')
    email = data.get('email')
    company = data.get('company')
    purpose = data.get('purpose')

    if not all([name, email]): # جعل الشركة والغرض اختياريين قليلاً
        return jsonify({'error': 'Missing required fields (name, email).'}), 400

    conn = None # تأكد من تعريف conn قبل try
    try:
        # 1. توليد مفتاح فريد (تحقق من عدم وجوده مسبقًا - نادر ولكنه ممكن)
        conn = get_db_connection()
        cur = conn.cursor()
        while True:
            license_key = generate_license_key()
            cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (license_key,))
            if cur.fetchone() is None:
                break # المفتاح فريد
        
        # 2. تخزين بيانات الترخيص في قاعدة البيانات
        insert_query = sql.SQL("""
            INSERT INTO licenses (license_key, name, email, company, purpose, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING; -- لا تسمح بنفس البريد الإلكتروني مرتين (أو يمكنك تحديث المفتاح؟)
        """)
        cur.execute(insert_query, (license_key, name, email, company, purpose, True))
        
        # التحقق مما إذا تم الإدراج (إذا لم يتم بسبب تعارض البريد الإلكتروني)
        if cur.rowcount == 0:
             cur.close()
             conn.close()
             print_error(f"Attempted to generate license for existing email: {email}")
             # يمكنك إما إرسال المفتاح القديم أو إرجاع خطأ
             return jsonify({'error': 'Email address already has a license key.'}), 409 # 409 Conflict

        conn.commit() # حفظ التغييرات في قاعدة البيانات
        print_error(f"License key {license_key} generated and stored for {email}.")

        # 3. إرسال البريد الإلكتروني
        send_email(email, license_key)

        return jsonify({'message': 'License key generated and sent successfully.'}), 201 # 201 Created

    except psycopg2.Error as db_err: # التعامل مع أخطاء قاعدة البيانات بشكل محدد
        print_error(f"Database Error: {db_err}")
        if conn: conn.rollback() # التراجع عن التغييرات في حالة الخطأ
        return jsonify({'error': f'Database operation failed: {db_err}'}), 500
    except ConnectionError as conn_err: # التعامل مع أخطاء الاتصال (بالبريد أو قاعدة البيانات)
         print_error(f"Connection Error: {conn_err}")
         if conn: conn.rollback()
         return jsonify({'error': str(conn_err)}), 503 # 503 Service Unavailable
    except Exception as e: # التعامل مع الأخطاء العامة الأخرى
        print_error(f"General Error in /generate-license: {e}")
        print_error(traceback.format_exc())
        if conn: conn.rollback()
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500
    finally:
        # تأكد دائمًا من إغلاق الاتصال
        if conn:
            conn.close()


# --- الخطوة التالية: إضافة نقطة نهاية /validate-license ---
# @app.route('/validate-license', methods=['POST'])
# def validate_license():
#     # ... (سيتم إضافتها في الخطوة التالية) ...
#     pass


# --- تشغيل التطبيق وإنشاء الجدول عند البدء ---
if __name__ == '__main__':
    print_error("Starting license API...")
    create_licenses_table_if_not_exists() # تأكد من وجود الجدول عند بدء تشغيل الخادم
    # استخدام Gunicorn بدلاً من app.run للإنتاج (يتم تكوينه في render.yaml)
    # app.run(host='0.0.0.0', port=10000) # فقط للاختبار المحلي
    print_error("License API setup complete. Waiting for requests...")

# --- END OF app.py (v2) ---
