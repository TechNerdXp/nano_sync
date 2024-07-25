import time
from flask import Flask, redirect, request, session, url_for, jsonify, render_template_string
from oauthlib.oauth2 import WebApplicationClient
import requests
import os
import json
from google.oauth2.credentials import Credentials
import gspread
import re
import random
from datetime import timedelta, datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Load credentials from the file
with open('credentials.json', 'r') as file:
    credentials = json.load(file)

GOOGLE_CLIENT_ID = credentials['web']['client_id']
GOOGLE_CLIENT_SECRET = credentials['web']['client_secret']
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.secret_key = 'HelloAndThisTheVeryTopOneOfTheTopSecretsOvTheWorldButItsNothingMan'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/www/nano_sync/nano_sync.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # It's a good practice to disable track modifications

db = SQLAlchemy(app)

class Spreadsheet(db.Model):
    id = db.Column(db.String, primary_key=True)
    last_update_time = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    current_index = db.Column(db.Integer, default=0)


def create_tables():
    db.create_all()

# Ensure the function is called within the application context
with app.app_context():
    create_tables()

client = WebApplicationClient(GOOGLE_CLIENT_ID)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()
    
def get_title_from_url(url):
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'
    ]
    
    headers = {'User-Agent': random.choice(user_agents)}
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        response = session.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            return title_match.group(1) if title_match else 'Title not found'
        else:
            return f'Error {response.status_code}'
    except requests.exceptions.RequestException as e:
        return f'Error fetching title: {str(e)}'
    
def refresh_token():
    refresh_token = session.get('refresh_token')
    if refresh_token:
        google_provider_cfg = get_google_provider_cfg()
        token_endpoint = google_provider_cfg["token_endpoint"]

        token_url, headers, body = client.prepare_refresh_token_request(
            token_endpoint,
            refresh_token=refresh_token
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        token_info = client.parse_request_body_response(json.dumps(token_response.json()))
        session['token'] = token_info['access_token']

def is_valid_token():
    if "token" in session:
        # Validate the token
        token_validation_response = requests.get(
            'https://www.googleapis.com/oauth2/v1/tokeninfo',
            params={'access_token': session['token']}
        )
        if token_validation_response.status_code == 200:
            return True
        elif "refresh_token" in session:
            try:
                refresh_token()
                # Validate the new token
                token_validation_response = requests.get(
                    'https://www.googleapis.com/oauth2/v1/tokeninfo',
                    params={'access_token': session['token']}
                )
                return token_validation_response.status_code == 200
            except Exception as e:
                app.logger.error(f'Error refreshing token: {e}')
    return False

def get_spreadsheet_status(spreadsheet_id):
    spreadsheet = Spreadsheet.query.get(spreadsheet_id)
    if spreadsheet is None:
        return {'status': 'error', 'message': 'Spreadsheet not found'}

    if datetime.now() - spreadsheet.last_update_time < timedelta(minutes=5):
        return {
            'status': 'running',
            'message': 'The spreadsheet is actively being processed. Please wait.',
            'current_row': spreadsheet.current_index
        }
    else:
        return {
            'status': 'idle',
            'message': 'The spreadsheet is currently idle and not undergoing any processing.',
            'current_row': spreadsheet.current_index
        }


@app.route("/nano_sync")
def index():
    spreadsheet_id = request.args.get('spreadsheet_id', None)
    sheet_name = request.args.get('sheet_name', None)
    return '''
        <html>
        <head>
            <title>Sheets App</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            <style>
                body {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    font-family: Arial, sans-serif;
                }}
                button {{
                    transition: background-color 0.3s ease;
                }}
                button:hover {{
                    opacity: 0.8;
                }}
            </style>
        </head>
        <body>
            <h1 class="text-2xl font-light mb-6">Sheets App</h1>
            <div id="message" class="text-lg font-light mb-4">Checking authentication status...</div>
            <div class="flex space-x-4">
                <button id="fetchTitlesButton" onclick="fetchTitles()" style="display: none;" class="bg-blue-500 hover:bg-blue-700 text-white font-light py-2 px-4 rounded cursor-pointer">Fetch Titles</button>
                <button id="revokeAuthenticationButton" onclick="revokeAuthentication()" style="display: none;" class="bg-red-500 hover:bg-red-700 text-white font-light py-2 px-4 rounded cursor-pointer">Revoke Authentication</button>
                <button id="authenticateButton" onclick="authenticate()" style="display: none" class="bg-green-500 hover:bg-green-700 text-white font-light py-2 px-4 rounded cursor-pointer">Authenticate</button>
            </div>
            <script>
            var spreadsheetId = '{0}';
            var sheetName = '{1}';

            function authenticate() {{
                var authWindow = window.open('/nano_sync/authenticate?spreadsheet_id=' + spreadsheetId + '&sheet_name=' + sheetName, '_blank', 'width=500,height=600');
            }}
            function fetchTitles() {{
                window.location.href = '/nano_sync/fetch_titles?spreadsheet_id=' + spreadsheetId + '&sheet_name=' + sheetName;
            }}
            function revokeAuthentication() {{
                fetch('/nano_sync/revoke_authentication')
                    .then(() => location.reload());
            }}
            function checkAuthenticationStatus() {{
                fetch('/nano_sync/check_authentication')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.authenticated) {{
                            document.getElementById('message').textContent = 'Hello, ' + data.email + '!';
                            document.getElementById('fetchTitlesButton').style.display = 'block';
                            document.getElementById('revokeAuthenticationButton').style.display = 'block';
                            document.getElementById('authenticateButton').style.display = 'none';
                        }} else {{
                            document.getElementById('message').textContent = 'You are not authenticated.';
                            document.getElementById('fetchTitlesButton').style.display = 'none';
                            document.getElementById('revokeAuthenticationButton').style.display = 'none';
                            document.getElementById('authenticateButton').style.display = 'block';
                        }}
                    }});
            }}
            checkAuthenticationStatus();
            </script>
        </body>
        </html>
    '''.format(spreadsheet_id, sheet_name)



@app.route("/nano_sync/authenticate")
def authenticate():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri='https://wiee.io/nano_sync/authenticate/callback',
        scope= [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        access_type='offline',
        prompt='consent',
    )
    return redirect(request_uri)

@app.route("/nano_sync/authenticate/callback")
def callback():
    session.permanent = True
    code = request.args.get("code")
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    token_info = client.parse_request_body_response(json.dumps(token_response.json()))
    session['token'] = token_info['access_token']
    if 'refresh_token' in token_info:
        session['refresh_token'] = token_info['refresh_token']
    else:
        app.logger.warning('Refresh token not found in the token response.')

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    email = userinfo_response.json()["email"]
    session['email'] = email

    return '''
        <html>
        <head>
            <title>Authentication Successful!</title>
        </head>
        <body>
            <p>Authentication successful! This window will close shortly.</p>
            <script>
            setTimeout(function() {
                window.opener.location.reload();
                window.close();
            }, 2000);
            </script>
        </body>
        </html>
    '''

@app.route("/nano_sync/revoke_authentication")
def revoke_authentication():
    if 'token' in session:
        requests.post('https://oauth2.googleapis.com/revoke',
            params={'token': session['token']},
            headers = {'content-type': 'application/x-www-form-urlencoded'})

    session.pop('refresh_token', None)
    session.pop('token', None)
    session.pop('email', None)
    return redirect(url_for("index"))

@app.route("/nano_sync/check_authentication")
def check_authentication():
    if is_valid_token():
        return jsonify({'authenticated': True, 'email': session['email']})
    else:
        return jsonify({'authenticated': False})
    
@app.route("/nano_sync/get_status")
def get_status():
    spreadsheet_id = request.args.get('spreadsheet_id', None)
    if not spreadsheet_id:
        return jsonify({'status': 'error', 'message': 'Missing spreadsheet_id'}), 400
    return jsonify(get_spreadsheet_status(spreadsheet_id))


@app.route('/nano_sync/view_logs')
def view_logs():
    log_path = '/var/www/nano_sync/error.log'  # Corrected path to your log file
    if os.path.exists(log_path):
        with open(log_path, 'r') as file:
            content = file.read()
        # Embedding HTML with a button to clear logs
        return render_template_string("""
            <html>
                <head>
                    <title>Log Viewer</title>
                </head>
                <body>
                    <button onclick="clearLogs()">Clear Logs</button>
                    <pre>{{ logs }}</pre>
                    <script>
                        function clearLogs() {
                            fetch('/clear_logs', { method: 'GET' })
                                .then(response => {
                                    if (response.ok) {
                                        window.location.reload();  // Reload page to update the log view
                                    } else {
                                        alert('Failed to clear logs');
                                    }
                                })
                                .catch(error => console.error('Error:', error));
                        }
                    </script>
                </body>
            </html>
        """, logs=content)
    else:
        return "Log file not found.", 404


@app.route('/nano_sync/clear_logs')
def clear_logs():
    log_path = '/var/www/nano_sync/error.log'  # Path to your log file
    try:
        # Open the file in write mode to clear its contents
        with open(log_path, 'w'):
            pass  # Opening in write mode without writing anything will clear the file
        return "Logs cleared successfully", 200
    except Exception as e:
        return f"Error clearing logs: {e}", 500


@app.route("/nano_sync/fetch_titles")
def fetch_titles():
    spreadsheet_id = request.args.get('spreadsheet_id', None)
    sheet_name = request.args.get('sheet_name', None)

    if not is_valid_token():
        return redirect(url_for('index', spreadsheet_id=spreadsheet_id, sheet_name=sheet_name))

    if not spreadsheet_id or not sheet_name:
        return jsonify({'status': 'error', 'message': 'Missing spreadsheet_id or sheet_name'}), 400

    status = get_spreadsheet_status(spreadsheet_id)
    if status['status'] == 'running':
        return jsonify({'status': 'error', 'message': 'The spreadsheet is currently being processed. Please wait.'}), 409

    creds = Credentials(session['token'])
    client = gspread.authorize(creds)

    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    data = sheet.get_all_records()
    headers = sheet.row_values(1)
    title_column = headers.index('Title') + 1
    commit_counter = 0
    # Fetch and update titles
    for i, row in enumerate(data, start=2):  # start=2 because get_all_records() starts at row 2
        url = row.get('URL')
        title = row.get('Title')
        if url and not title:
            time.sleep(5)
            title = get_title_from_url(url)
            sheet.update_cell(i, title_column, title)
            
            spreadsheet = Spreadsheet.query.get(spreadsheet_id)
            if spreadsheet is None:
                spreadsheet = Spreadsheet(id=spreadsheet_id)
                db.session.add(spreadsheet)
            spreadsheet.last_update_time = datetime.now()
            spreadsheet.current_index = i
            
        commit_counter += 1
        if commit_counter >= 10:
            db.session.commit()
            commit_counter = 0

    # Final commit to capture any remaining changes
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Titles fetched and updated successfully.'})
    