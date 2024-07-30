from datetime import datetime, timezone
import os
from flask import Blueprint, request, jsonify, redirect, session, render_template_string, url_for
import gspread
from app.utils import copy_data, get_google_provider_cfg, is_valid_token, get_access_token, get_client_config, log_debug, save_token
from flask import current_app
from .extensions import db
from app.models import RefreshToken, Token, User
from oauthlib.oauth2 import WebApplicationClient  # Import WebApplicationClient
from google.oauth2.credentials import Credentials
import json
import requests

main = Blueprint('main', __name__)

credentials = get_client_config()

GOOGLE_CLIENT_ID = credentials['client_id']
GOOGLE_CLIENT_SECRET = credentials['client_secret']
REDIRECT_URIS = credentials['redirect_uris']


client = WebApplicationClient(GOOGLE_CLIENT_ID)  # Use your actual Google Client ID

@main.route("/nano_sync/")
def index():
    source_ss_id = request.args.get('source_ss_id', None)
    source_sheet_name = request.args.get('source_sheet_name', None)
    target_ss_id = request.args.get('target_ss_id', None)
    target_sheet_name = request.args.get('target_sheet_name', None)
    return render_template_string("""
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
                <button id="copyDataButton" onclick="copyData()" style="display: none;" class="bg-blue-500 hover:bg-blue-700 text-white font-light py-2 px-4 rounded cursor-pointer">Copy Data</button>
                <button id="revokeAuthenticationButton" onclick="revokeAuthentication()" style="display: none;" class="bg-red-500 hover:bg-red-700 text-white font-light py-2 px-4 rounded cursor-pointer">Revoke Authentication</button>
                <button id="authenticateButton" onclick="authenticate()" style="display: none" class="bg-green-500 hover:bg-green-700 text-white font-light py-2 px-4 rounded cursor-pointer">Authenticate</button>
            </div>
            <script>
            var sourceSsId = '{0}';
            var sourceSheetName = '{1}';
            var targetSsId = '{2}';
            var targetSheetName = '{3}';

            function authenticate() {{
                var authWindow = window.open('/nano_sync/authenticate?source_ss_id=' + sourceSsId + '&source_sheet_name=' + sourceSheetName + '&target_ss_id=' + targetSsId + '&target_sheet_name=' + targetSheetName, '_blank', 'width=500,height=600');
            }}
            function copyData() {{
                window.location.href = '/nano_sync/copy_data?src_ss_id=' + sourceSsId + '&src_sheet_name=' + sourceSheetName + '&dest_ss_id=' + targetSsId + '&dest_sheet_name=' + targetSheetName;
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
                            document.getElementById('copyDataButton').style.display = 'block';
                            document.getElementById('revokeAuthenticationButton').style.display = 'block';
                            document.getElementById('authenticateButton').style.display = 'none';
                        }} else {{
                            document.getElementById('message').textContent = 'You are not authenticated.';
                            document.getElementById('copyDataButton').style.display = 'none';
                            document.getElementById('revokeAuthenticationButton').style.display = 'none';
                            document.getElementById('authenticateButton').style.display = 'block';
                        }}
                    }});
            }}
            checkAuthenticationStatus();
            </script>
        </body>
        </html>
    """.format(source_ss_id, source_sheet_name, target_ss_id, target_sheet_name))


@main.route("/nano_sync/authenticate")
def authenticate():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri= REDIRECT_URIS[0],
        scope=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        access_type='offline',
        prompt='consent'
    )
    return redirect(request_uri)

@main.route("/nano_sync/authenticate/callback")
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
        print('Refresh token not found in the token response.')

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    email = userinfo_response.json()["email"]
    session['email'] = email
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()

    expires_in = 60 * 60
    save_token(user.id, token_info['access_token'], token_info.get('refresh_token'), expires_in)
    session['user_id'] = user.id

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

@main.route("/nano_sync/revoke_authentication")
def revoke_authentication():
    """
    Revokes the refresh and access tokens for the specified user.
    """
    user_id = session.get('user_id')
    # Remove refresh token from the database
    refresh_token = RefreshToken.query.filter_by(user_id=user_id).first()
    if refresh_token:
        db.session.delete(refresh_token)

    # Remove access token from the database and revoke it using Google OAuth2 API if it's stored in session
    token = Token.query.filter_by(user_id=user_id).first()
    if token:
        if 'token' in session:
            requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': session['token']},
                headers={'content-type': 'application/x-www-form-urlencoded'}
            )
        db.session.delete(token)

    # Commit the changes to the database
    db.session.commit()

    # Clear session data
    session.pop('refresh_token', None)
    session.pop('token', None)
    session.pop('email', None)
    session.pop('user_id', None)
    return redirect(main.index)

@main.route("/nano_sync/check_authentication")
def check_authentication():
    user_id = session.get('user_id')
    if user_id and is_valid_token(user_id):
        user = User.query.get(user_id)
        return jsonify({'authenticated': True, 'email': user.email})
    else:
        session.clear()
        return jsonify({'authenticated': False})

@main.route('/nano_sync/copy_data', methods=['GET'])
def copy_data_route():
    source_ss_id = request.args.get('src_ss_id')
    source_sheet_name = request.args.get('src_sheet_name')
    target_ss_id = request.args.get('dest_ss_id')
    target_sheet_name = request.args.get('dest_sheet_name')
    
    source_ss_id = None if source_ss_id == "None" else source_ss_id
    source_sheet_name = None if source_sheet_name == "None" else source_sheet_name
    target_ss_id = None if target_ss_id == "None" else target_ss_id
    target_sheet_name = None if target_sheet_name == "None" else target_sheet_name

    if not all([source_ss_id, source_sheet_name, target_ss_id, target_sheet_name]):
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Get the user ID from the session
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('main.index', source_ss_id=source_ss_id, source_sheet_name=source_sheet_name, target_ss_id=target_ss_id, target_sheet_name=target_sheet_name))
        
        # Retrieve tokens and client credentials
        token = Token.query.filter_by(user_id=user_id).first()
        refresh_token = RefreshToken.query.filter_by(user_id=user_id).first()


        access_token = token.access_token
        refresh_token_value = refresh_token.refresh_token
        client_id = GOOGLE_CLIENT_ID
        client_secret = GOOGLE_CLIENT_SECRET
        
        google_provider_cfg = get_google_provider_cfg()
        token_uri = google_provider_cfg["token_endpoint"]
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token_value,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret
        )

        client = gspread.authorize(credentials)

        copy_data(client, source_ss_id, source_sheet_name, target_ss_id, target_sheet_name)
        return jsonify({"message": "Data copied successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Debugging...

@main.route('/nano_sync/view_logs')
def view_logs():
    log_path = '/var/www/nano_sync/error.log'
    try:
        with open(log_path, 'r') as file:
            content = file.read()
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
                            fetch('/nano_sync/clear_logs', { method: 'GET' })
                                .then(response => {
                                    if (response.ok) {
                                        alert('Logs cleared successfully.');
                                        window.location.reload();
                                    } else {
                                        alert('Failed to clear logs.');
                                    }
                                })
                                .catch(error => console.error('Error:', error));
                        }
                    </script>
                </body>
            </html>
        """, logs=content)
    except IOError:
        return "Log file not found.", 404

@main.route('/nano_sync/clear_logs')
def clear_logs():
    log_path = '/var/www/nano_sync/error.log'
    try:
        with open(log_path, 'w'):
            pass
        return "Logs cleared successfully", 200
    except Exception as e:
        return f"Error clearing logs: {e}", 500
    
# Debugging
@main.route('/nano_sync/user/<int:user_id>', methods=['GET'])
def get_user_info(user_id):
    # Query the User, Token, and RefreshToken tables
    user = User.query.get(user_id)
    token = Token.query.filter_by(user_id=user_id).first()
    refresh_token = RefreshToken.query.filter_by(user_id=user_id).first()

    if user and token and refresh_token:
        # If the user and tokens exist, return their information
        return jsonify({
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'registered_on': user.registered_on.isoformat()
            },
            'token': {
                'access_token': token.access_token,
                'expiry': token.expiry.isoformat()
            },
            'refresh_token': {
                'refresh_token': refresh_token.refresh_token
            },
            'server_time': datetime.now(timezone.utc).isoformat()  # Current server time
        }), 200
    else:
        # If the user or tokens do not exist, return an error message
        return jsonify({'error': 'User not found'}), 404