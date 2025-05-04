# render.yaml (v1.1 - Using Gunicorn)
# This file configures the deployment of the Flask API on Render.com

services:
  # Defines the web service for the license API
  - type: web        # Type of service: web server
    name: clashpilot-license-api # Name of the service on Render dashboard
    env: python      # Runtime environment: Python
    plan: free       # Render plan (adjust if needed, e.g., 'starter')
    region: frankfurt # Optional: Specify a region (e.g., Frankfurt, Oregon) - choose one close to you/users
    # Commands to build the service
    buildCommand: pip install -r requirements.txt # Install dependencies
    # Command to start the service using Gunicorn WSGI server
    startCommand: gunicorn app:app # Tells Gunicorn to run the 'app' instance from the 'app.py' file
    # Environment variables needed by the application
    envVars:
      - key: DATABASE_URL       # Connection string for PostgreSQL database
        sync: false           # Value will be set manually in Render dashboard (from DB service)
      - key: EMAIL_PASSWORD     # Password for the sender email account
        sync: false           # Value will be set manually in Render dashboard
      # Optional: Set Python version if needed (Render defaults work fine usually)
      # - key: PYTHON_VERSION
      #   value: 3.11.11
      # Optional: Set SENDER_EMAIL if different from default in app.py
      # - key: SENDER_EMAIL
      #   value: your_email@example.com
      # Optional: Set SMTP Host/Port if different from default in app.py
      # - key: SMTP_HOST
      #   value: smtp.yourprovider.com
      # - key: SMTP_PORT
      #   value: 587

# Note: Render automatically injects a PORT environment variable (usually 10000)
# Gunicorn automatically binds to 0.0.0.0 and this PORT, so explicitly setting
# HOST or PORT variables here is typically not required unless you have specific needs.
