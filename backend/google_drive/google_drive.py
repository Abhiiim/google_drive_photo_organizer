from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import pickle
import os
import re
from typing import List, Dict, Optional

SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveClient:
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        creds = None
        
        # Load existing credentials
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    print("Refresh token expired, need to re-authenticate")
                    creds = None

            print(f"CRED 1: {creds}")
            
            if not creds:
                if not os.path.exists('credentials.json'):
                    raise Exception("credentials.json not found. Please download from Google Cloud Console.")
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    print(f"CRED 2: {creds}")
                    print(f"FLOW: {flow}")
                    
                    # First try local server with different settings
                    try:
                        print("Trying local server authentication...")
                        creds = flow.run_local_server(
                            host='localhost',
                            port=8080,
                            open_browser=True,  # Don't auto-open browser
                            bind_addr=None
                        )
                        print(f"CRED SUCCESS: Local server authentication completed")
                    except Exception as local_error:
                        print(f"Local server failed: {local_error}")
                        
                        # Manual console authentication
                        print("\n" + "="*60)
                        print("MANUAL AUTHENTICATION REQUIRED")
                        print("="*60)
                        
                        # Get the authorization URL
                        auth_url, _ = flow.authorization_url(prompt='consent')
                        
                        print(f"\n1. Open this URL in your browser:")
                        print(f"{auth_url}")
                        print(f"\n2. Complete the authorization process")
                        print(f"3. Copy the ENTIRE redirect URL from your browser")
                        print(f"   (It will look like: http://localhost/?code=...)")
                        print(f"4. Paste it below and press Enter")
                        
                        # Get the authorization response from user
                        auth_response = input("\nPaste the full redirect URL here: ").strip()
                        
                        # Extract the authorization code
                        flow.fetch_token(authorization_response=auth_response)
                        creds = flow.credentials
                        print(f"CRED SUCCESS: Manual authentication completed")

                except Exception as e:
                    print(f"Full error: {e}")
                    raise Exception(f"Authentication failed: {str(e)}. Please check your OAuth consent screen configuration.")
            
            # Save credentials for next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
    
    def extract_folder_id(self, folder_link: str) -> str:
        """Extract folder ID from Google Drive link"""
        patterns = [
            r'/folders/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
            r'^([a-zA-Z0-9-_]+)$'  # Direct ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, folder_link)
            if match:
                return match.group(1)
        
        raise ValueError("Invalid Google Drive folder link")
    
    def list_images(self, folder_id: str) -> List[Dict]:
        """List all image files in folder"""
        try:
            # First, try to get folder info to check if we have access
            folder_info = self.service.files().get(fileId=folder_id).execute()
            print(f"Folder found: {folder_info.get('name')} (ID: {folder_id})")
            
            query = f"'{folder_id}' in parents and (mimeType contains 'image/')"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)",
                pageSize=1000
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            print(f"Error accessing folder {folder_id}: {e}")
            raise Exception(f"Cannot access folder. Please check: 1) Folder exists 2) You have access 3) Folder ID is correct. Error: {str(e)}")
    
    def download_file(self, file_id: str, file_path: str):
        """Download file from Google Drive"""
        request = self.service.files().get_media(fileId=file_id)
        
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
    
    def create_folder(self, name: str, parent_id: str) -> str:
        """Create folder in Google Drive"""
        try:
            # First check if we have write permissions to the parent folder
            parent_info = self.service.files().get(
                fileId=parent_id,
                fields='capabilities'
            ).execute()
            
            capabilities = parent_info.get('capabilities', {})
            can_add_children = capabilities.get('canAddChildren', False)
            
            if not can_add_children:
                raise Exception(f"No permission to create folders in the specified location. You need 'Editor' access to this folder.")
            
            folder_metadata = {
                'name': name,
                'parents': [parent_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            print(f"Created folder: {name} (ID: {folder.get('id')})")
            return folder.get('id')
            
        except Exception as e:
            if "insufficientParentPermissions" in str(e):
                raise Exception(f"Cannot create folders - you need 'Editor' permission for this Google Drive folder. Current access is read-only.")
            else:
                raise Exception(f"Failed to create folder '{name}': {str(e)}")
    
    def move_file(self, file_id: str, new_parent_id: str, old_parent_id: str):
        """Move file to new folder"""
        self.service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=old_parent_id
        ).execute()
    
    def create_shortcut(self, target_file_id: str, parent_folder_id: str, name: str):
        """Create shortcut to file in specified folder"""
        shortcut_metadata = {
            'name': name,
            'parents': [parent_folder_id],
            'mimeType': 'application/vnd.google-apps.shortcut',
            'shortcutDetails': {
                'targetId': target_file_id
            }
        }
        
        self.service.files().create(body=shortcut_metadata).execute()
    
    def test_access(self):
        """Test basic Drive access and list user's folders"""
        try:
            print("Testing Google Drive access...")
            
            # List some folders in user's Drive
            results = self.service.files().list(
                q="mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name, parents)",
                pageSize=10
            ).execute()
            
            folders = results.get('files', [])
            print(f"\nFound {len(folders)} folders in your Drive:")
            for folder in folders:
                print(f"  - {folder['name']} (ID: {folder['id']})")
            
            return folders
            
        except Exception as e:
            print(f"Drive access test failed: {e}")
            return []
    
    def create_test_folder(self) -> str:
        """Create a test folder in user's Drive root"""
        try:
            folder_metadata = {
                'name': 'Face_Organizer_Test',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id,name'
            ).execute()
            
            folder_id = folder.get('id')
            folder_name = folder.get('name')
            
            print(f"Created test folder: {folder_name} (ID: {folder_id})")
            print(f"You can access it at: https://drive.google.com/drive/folders/{folder_id}")
            
            return folder_id
            
        except Exception as e:
            print(f"Failed to create test folder: {e}")
            raise
    
    def check_folder_permissions(self, folder_id: str) -> Dict[str, bool]:
        """Check what permissions we have on a folder"""
        try:
            folder_info = self.service.files().get(
                fileId=folder_id,
                fields='name,capabilities,permissions'
            ).execute()
            
            capabilities = folder_info.get('capabilities', {})
            
            permissions = {
                'can_read': capabilities.get('canListChildren', False),
                'can_create_folders': capabilities.get('canAddChildren', False),
                'can_move_files': capabilities.get('canMoveItemIntoTeamDrive', True),  # Usually true for owned folders
                'can_edit': capabilities.get('canEdit', False),
                'folder_name': folder_info.get('name', 'Unknown')
            }
            
            return permissions
            
        except Exception as e:
            raise Exception(f"Cannot check folder permissions: {str(e)}")