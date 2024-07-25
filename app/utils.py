import time
from memory_profiler import memory_usage
import requests
import json
from datetime import datetime, timezone, timedelta
from app import db
from app.models import Token, RefreshToken
from oauthlib.oauth2 import WebApplicationClient  # Import WebApplicationClient


def get_google_provider_cfg():
    return requests.get("https://accounts.google.com/.well-known/openid-configuration").json()

def get_client_config():
    with open('credentials.json', 'r') as file:
        data = json.load(file)
    return data['web']

credentials = get_client_config()

GOOGLE_CLIENT_ID = credentials['client_id']
GOOGLE_CLIENT_SECRET = credentials['client_secret']

client = WebApplicationClient(GOOGLE_CLIENT_ID)  # Use your actual Google Client ID

def save_token(user_id, access_token, refresh_token, expires_in):
    """
    Saves or updates the access and refresh tokens for a user.
    """
    token = Token.query.filter_by(user_id=user_id).first()
    if not token:
        token = Token(user_id=user_id)
        db.session.add(token)
    token.access_token = access_token
    if expires_in:
        token.expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    else:
        token.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    db.session.commit()  # Commit changes for the access token and expiry

    if refresh_token:
        r_token = RefreshToken.query.filter_by(user_id=user_id).first()
        if not r_token:
            r_token = RefreshToken(user_id=user_id, refresh_token=refresh_token)
            db.session.add(r_token)
        else:
            r_token.refresh_token = refresh_token

        db.session.commit()  # Commit changes for the refresh token


def get_access_token(user_id):
    token = Token.query.filter_by(user_id=user_id).first()
    
    if token and token.expiry.tzinfo is None:
        token.expiry = token.expiry.replace(tzinfo=timezone.utc)
    
    if token and token.expiry > datetime.now(timezone.utc):
        return token.access_token
    log_debug('trying to refreshhhh it from get access token')
    return refresh_access_token(user_id)
  
def refresh_access_token(user_id):
    refresh_token = RefreshToken.query.filter_by(user_id=user_id).first()
    if refresh_token:
        google_provider_cfg = get_google_provider_cfg()
        token_endpoint = google_provider_cfg["token_endpoint"]

        token_url, headers, body = client.prepare_refresh_token_request(
            token_endpoint,
            refresh_token=refresh_token.refresh_token
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        if token_response.status_code == 200:
            token_info = client.parse_request_body_response(json.dumps(token_response.json()))
            log_debug(token_info)
            save_token(user_id, token_info['access_token'], None, token_info['expires_in'])
            return token_info['access_token']
        else:
            print(f"Error refreshing token: {token_response.text}")
            return None

def is_valid_token(user_id):
    token = Token.query.filter_by(user_id=user_id).first()
    if not token:
        return False
    
    if token.expiry.tzinfo is None:
        token.expiry = token.expiry.replace(tzinfo=timezone.utc)
    
    if token.expiry <= datetime.now(timezone.utc):
        refreshed_token = refresh_access_token(user_id)
        return refreshed_token is not None

    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v1/tokeninfo',
            params={'access_token': token.access_token}
        )
        if response.status_code == 200:
            return True
        else:
            refreshed_token = refresh_access_token(user_id)
            return refreshed_token is not None
    except requests.RequestException as e:
        print(f"Error validating token: {str(e)}")
        return False


    
    
def log_debug(message: str, log_file: str = "error.log"):
    """
    Logs a debug message to the specified log file with a distinct line separator.

    Args:
    - message (str): The debug message to log.
    - log_file (str): The path to the log file. Defaults to 'debug.log'.
    """
    with open(log_file, "a") as file:
        file.write("\n" + "="*50 + "\n")
        file.write(f"{message}\n")
        file.write("="*50 + "\n")
        


def copy_data(client, source_ss_id, source_sheet_name, target_ss_id, target_sheet_name):
    """
    Copy data from one Google Sheet to another efficiently in chunks of 2000 rows.
    """
    CHUNK_SIZE = 2000  # Number of rows per chunk
    log_debug('inside data copying')
    
    source_sheet = client.open_by_key(source_ss_id).worksheet(source_sheet_name)
    dest_sheet = client.open_by_key(target_ss_id).worksheet(target_sheet_name)

    # Get all data from the source sheet
    data = source_sheet.get_all_values()
    total_rows = len(data)

    # Clear the destination sheet (optional, if you want to overwrite)
    dest_sheet.clear()

    # Process and update in chunks
    start_time = time.time()  # Start time
    start_mem = memory_usage()[0]  # Start memory usage

    for start in range(0, total_rows, CHUNK_SIZE):
        end = start + CHUNK_SIZE
        chunk = data[start:end]

        # Update the destination sheet with the chunk of data
        range_str = f'A{start + 1}'
        dest_sheet.update(range_str, chunk)

        log_debug(f"Copied rows {start + 1} to {end}")
        
        # Sleep for a few seconds to avoid hitting rate limits
        time.sleep(5)  # Sleep for 3 seconds

    end_time = time.time()  # End time
    end_mem = memory_usage()[0]  # End memory usage

    log_debug("Data copied successfully!")
    log_debug(f"Execution time: {end_time - start_time} seconds")
    log_debug(f"Memory used: {end_mem - start_mem} MiB")














# def copy_data(client, source_ss_id, source_sheet_name, target_ss_id, target_sheet_name):
#     """
#     Copy data from one Google Sheet to another efficiently in chunks of 2000 rows.
#     """
#     CHUNK_SIZE = 2000  # Number of rows per chunk
#     log_debug('inside data copying')
    
#     source_sheet = client.open_by_key(source_ss_id).worksheet(source_sheet_name)
#     dest_sheet = client.open_by_key(target_ss_id).worksheet(target_sheet_name)

#     # Get all data from the source sheet
#     data = source_sheet.get_all_values()
#     total_rows = len(data)

#     # Clear the destination sheet (optional, if you want to overwrite)
#     dest_sheet.clear()

#     # Process and update in chunks
#     for start in range(0, total_rows, CHUNK_SIZE):
#         end = start + CHUNK_SIZE
#         chunk = data[start:end]

#         # Update the destination sheet with the chunk of data
#         range_str = f'A{start + 1}'
#         dest_sheet.update(range_str, chunk)

#         log_debug(f"Copied rows {start + 1} to {end}")
        
#         # Sleep for a few seconds to avoid hitting rate limits
#         time.sleep(5)  # Sleep for 3 seconds

#     print("Data copied successfully!")

        