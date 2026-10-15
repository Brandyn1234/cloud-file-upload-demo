import os 
import json 
import boto3

# configuration from Lambda's built-in environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

ses = boto3.client('ses', region_name=AWS_REGION)

def lambda_handler(event, context):
    file_url = event.get('file_url')
    recipient_emails = event.get('emails', [])

    if not file_url or not recipient_emails:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing file URL or recipient emails.')
        }

    subject = "A file has been shared with you!"
    body_text = f"Hello,\n\nA file has been uploaded and shared with you. You can download it here:\n{file_url}\n\nBest regards,\nFile Sharing App"
    body_html = f"""<html>
    <head></head>
    <body>
      <h1>File Shared With You</h1>
      <p>A file has been uploaded and shared with you.</p>
      <p><a href="{file_url}">Click here to download your file</a></p>
    </body>
    </html>"""

    for recipient in recipient_emails:
        try:
            ses.send_email(
                Source=SENDER_EMAIL,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                        'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                    }
                }
            )
            print(f"Email sent successfully to {recipient}")
        except Exception as e:
            print(f"Failed to send email to {recipient}: {str(e)}")
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Emails sent successfully!')
    }

