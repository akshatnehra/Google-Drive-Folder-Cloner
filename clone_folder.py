from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.auth.transport.requests import AuthorizedSession
import os

# replace with your folder ID and destination folder ID
FOLDER_ID = 'SOURCE_FOLDER_ID'
DESTINATION_FOLDER_ID = 'DESTINATION_FOLDER-ID'

SCOPES = ['https://www.googleapis.com/auth/drive']

creds = None
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

drive_service = build('drive', 'v3', credentials=creds)

# Get folder metadata
folder = drive_service.files().get(fileId=FOLDER_ID).execute()

# Recursively copy folder and its contents to destination folder
def copy_folder(folder_id, destination_folder_id):
    folder = drive_service.files().get(fileId=folder_id).execute()
    folder_name = folder['name']
    print(f'Copying folder "{folder_name}"')
    new_folder = {'name': folder_name, 'parents': [destination_folder_id], 'mimeType': 'application/vnd.google-apps.folder'}
    created_folder = drive_service.files().create(body=new_folder).execute()
    new_folder_id = created_folder['id']
    results = drive_service.files().list(q=f"'{folder_id}' in parents", fields="nextPageToken, files(id, name, createdTime, mimeType, size)").execute()
    items = results.get('files', [])
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            copy_folder(item['id'], new_folder_id)
        else:
            print(f'Copying file "{item["name"]}"')
            new_file = {'name': item['name'], 'parents': [new_folder_id]}
            try:
                drive_service.files().copy(fileId=item['id'], body=new_file).execute()
            except HttpError as error:
                if error.resp.status == 403 and 'cannotCopyFile' in str(error):
                    print(f'Error copying file "{item["name"]}": {error}')
                else:
                    raise

copy_folder(FOLDER_ID, DESTINATION_FOLDER_ID)
print('Done copying folder and its contents')
