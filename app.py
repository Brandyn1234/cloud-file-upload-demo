import os 
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for
import boto3
from dotenv import load_dotenv

# Load the variables from the .env file 
load_dotenv()

app = Flask(__name__)

# configuration from the environment 
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME")
APP_PASSCODE = os.getenv("APP_PASSCODE", "secret123")

# Initialize AWS SDK clients (Ohio region)
s3 = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)

# Set allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    return redirect(url_for('upload_page'))

@app.route('/upload-screen')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Passcode validation
    provided_passcode = request.form.get('passcode')
    if provided_passcode != APP_PASSCODE:
        return "Unauthorized: Invalid passcode!", 401
    
    uploaded_file = request.files.get('file')
    recipient_emails = [e.strip() for e in request.form.getlist('emails') if e.strip()]

    if uploaded_file and uploaded_file.filename != '':
        if not allowed_file(uploaded_file.filename):
            return "File type not permitted!", 400
        
        file_name = uploaded_file.filename
        file_id = str(uuid.uuid4())
        s3_key = f"uploads/{file_id}_{file_name}"

        # Step A: Stream file directly to AWS S3
        s3.upload_fileobj(
            uploaded_file,
            S3_BUCKET_NAME,
            s3_key
        )
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

        # Step B: Record upload in AWS DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        table.put_item(
            Item={
                'file_id': file_id,
                'file_name': file_name,
                's3_url': file_url,
                'recipients': recipient_emails
            }
        )

        # Step C: Trigger Lambda function to send emails via SES
        payload_dict = {
            "file_url": file_url,
            "emails": recipient_emails
        }
        payload_data = json.dumps(payload_dict)

        lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='Event',
            Payload=payload_data.encode('utf-8')
        )

        return "<h3>File uploaded successfully! Emails are being dispatched.</h3>"

    return "No file selected!", 400

if __name__ == '__main__':

    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1")

    app.run(host='127.0.0.1', port=port, debug=debug)

