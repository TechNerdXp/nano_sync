from app import db
from app.models import Token
from app.utils import get_title_from_url, log_debug, refresh_access_token, is_valid_token
from flask import current_app
import gspread
from google.oauth2.credentials import Credentials

def fetch_and_update_titles(spreadsheet_id, sheet_name, user_id):
    # log_debug(f"Starting fetch_and_update_titles task for user_id: {user_id}, spreadsheet_id: {spreadsheet_id}, sheet_name: {sheet_name}")

    # try:
    #     log_debug("Inside try block")
        
    #     # Ensure the token is valid before proceeding
    #     if not is_valid_token(user_id):
    #         log_debug("Token is not valid")
    #         if not refresh_access_token(user_id):
    #             log_debug("Token refresh failed")
    #             current_app.logger.error(f"Token refresh failed for user {user_id}")
    #             return "Token refresh failed"
    #     else:
    #         log_debug("Token is valid")

    #     token = Token.query.filter_by(user_id=user_id).first()
    #     creds = Credentials(token=token.access_token)  # Reauthorize with the refreshed token
    #     client = gspread.authorize(creds)
    #     log_debug("Authorized Google Sheets API client")

    #     sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    #     data = sheet.get_all_records()
    #     headers = sheet.row_values(1)
    #     title_column = headers.index('Title') + 1
    #     commit_counter = 0
    #     log_debug("Fetched data from Google Sheet")

    #     # Fetch and update titles
    #     for i, row in enumerate(data, start=2):  # Start from second row as headers are in the first
    #         url = row.get('URL')
    #         title = row.get('Title')
    #         if url and not title:
    #             title = get_title_from_url(url)
    #             sheet.update_cell(i, title_column, title)
    #             log_debug(f"Updated title for URL: {url} in row {i}")

    #             google_sheet = GoogleSheet.query.get(spreadsheet_id)
    #             if google_sheet is None:
    #                 google_sheet = GoogleSheet(id=spreadsheet_id, user_id=user_id, sheet_id=sheet_name)
    #                 db.session.add(google_sheet)
    #             google_sheet.start_process()

    #             commit_counter += 1
    #             if commit_counter >= 10:
    #                 db.session.commit()
    #                 commit_counter = 0
    #                 log_debug("Committed batch of updates to database")

    #     # Final commit to ensure all changes are captured
    #     db.session.commit()
    #     log_debug("Final commit of updates to database")

    # except Exception as e:
    #     current_app.logger.error(f"Failed to update titles: {str(e)}")
    #     log_debug(f"Failed to update titles: {str(e)}")
    #     return "Failed to update titles"
    pass

