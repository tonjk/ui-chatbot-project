import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from werkzeug.utils import secure_filename
import pandas as pd
from utils import s3_upload_file

load_dotenv()

app = Flask(__name__, template_folder='templates')

# --- GOOGLE SHEETS API SETUP ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# Load service account JSON from environment variable
# credentials_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
creds = service_account.Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]))
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()


# --- FLASK ROUTES ---

# Route to serve the main HTML form
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle the form submission
@app.route('/save-config', methods=['POST'])
def save_config():
    print("Received form data for saving configuration.")
    try:
        # --- PARSE FORM DATA ---
        form_data = request.form
        bot_name = form_data.get('bot_name')
        greeting_message = form_data.get('greeting_message')
        persona = form_data.get('persona')

        # Handle logo upload
        logo_file = request.files.get('bot_logo')
        logo_filepath = ""
        if logo_file and allowed_file(logo_file.filename):
            logo_filename = secure_filename(logo_file.filename)
            logo_filename = f"{bot_name}_logo.{logo_filename.rsplit('.', 1)[1].lower()}".replace(" ", "+")
            logo_file.seek(0)
            logo_filepath = s3_upload_file(logo_file, logo_filename)
        
        # Handle template file upload
        template_file = request.files.get('template_file')
        template_filename = template_file.filename if template_file else 'N/A'
        qa_pairs = []
        template_path = ""
        if template_file and allowed_file(template_file.filename):
            template_filename = secure_filename(template_file.filename)
            template_filename = f"{bot_name}_template.{template_filename.rsplit('.', 1)[1].lower()}".replace(" ", "+")
            template_file.seek(0)
            template_path = s3_upload_file(template_file, template_filename)
            
            # Parse Excel/CSV file to extract Q&A pairs
            try:
                if template_filename.endswith('.csv'):
                    df = pd.read_csv(template_path)
                else:
                    df = pd.read_excel(template_path)
                
                # Assume first two columns are question and answer
                if len(df.columns) >= 2:
                    for _, row in df.iterrows():
                        qa_pairs.append({
                            'question': str(row.iloc[0]),
                            'answer': str(row.iloc[1])
                        })
                qa_pairs = json.dumps(qa_pairs)  # Convert to JSON string for storage
                
            except Exception as e:
                print(f"Error parsing template file: {e}")
        
        # Get manual Q&A pairs if no file was uploaded
        if not qa_pairs:
            questions = request.form.getlist('questions[]')
            answers = request.form.getlist('answers[]')
            for q, a in zip(questions, answers):
                if q.strip() and a.strip():
                    qa_pairs.append({
                        'question': q.strip(),
                        'answer': a.strip()
                    })
            qa_pairs = json.dumps(qa_pairs)  # Convert to JSON string for storage

        # Handle dynamic key-value pairs
        config_keys = form_data.getlist('config_keys[]')
        config_values = form_data.getlist('config_values[]')
        additional_config = json.dumps({k: v for k, v in zip(config_keys, config_values)})

        # --- PREPARE DATA FOR GOOGLE SHEET ---
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # The order must match the columns in your sheet
        row_data = [
            timestamp,
            bot_name,
            greeting_message,
            persona,
            logo_filepath,
            template_path,
            template_filename,
            qa_pairs,
            additional_config
        ]

        # --- APPEND DATA TO GOOGLE SHEET ---
        # The range 'Sheet1' tells the API to append to the first available row in that sheet.
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row_data]}
        ).execute()
        
        print(f"Appended data: {result}")
        
        return jsonify({'status': 'success', 'message': 'Configuration saved successfully!'})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# --- RUN THE APP ---
if __name__ == '__main__':
    app.run(debug=True, port=8080)