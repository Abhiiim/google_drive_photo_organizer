from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import pickle
import os
import re
from typing import Dict, List, Optional

from core.config import get_settings
from core.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)

SCOPES = list(settings.google_scopes)

class GoogleDriveClient:
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """
        Authenticate with Google Drive API using OAuth2
        
        Raises:
            Exception: If authentication fails
        """
        creds = None
        
        try:
            # Load existing credentials
            if os.path.exists('token.pickle'):
                try:
                    with open('token.pickle', 'rb') as token:
                        creds = pickle.load(token)
                    logger.info("google_drive.credentials_loaded")
                except Exception as e:
                    logger.warning(
                        "google_drive.credentials_load_failed",
                        error=str(e),
                    )
                    creds = None
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("google_drive.credentials_refresh_start")
                        creds.refresh(Request())
                        logger.info("google_drive.credentials_refresh_success")
                    except RefreshError as e:
                        logger.warning(
                            "google_drive.credentials_refresh_expired",
                            error=str(e),
                        )
                        creds = None
                    except Exception as e:
                        logger.warning(
                            "google_drive.credentials_refresh_error",
                            error=str(e),
                        )
                        creds = None

                logger.debug("google_drive.credentials_state", creds=str(creds))
                
                if not creds:
                    if not os.path.exists('credentials.json'):
                        raise Exception("❌ credentials.json not found. Please download from Google Cloud Console.")
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                        logger.debug(
                            "google_drive.oauth_flow_initialized",
                            scopes=SCOPES,
                        )

                        # First try local server with different settings
                        try:
                            logger.info("google_drive.oauth_local_server_start")
                            creds = flow.run_local_server(
                                host='localhost',
                                port=8080,
                                open_browser=True,
                                bind_addr=None,
                            )
                            logger.info("google_drive.oauth_local_server_success")
                        except Exception as local_error:
                            logger.warning(
                                "google_drive.oauth_local_server_failed",
                                error=str(local_error),
                            )

                            # Manual console authentication
                            logger.info("google_drive.oauth_manual_required")
                            print("\n" + "=" * 60)
                            print("MANUAL AUTHENTICATION REQUIRED")
                            print("=" * 60)

                            # Get the authorization URL
                            auth_url, _ = flow.authorization_url(prompt='consent')

                            logger.info("google_drive.oauth_manual_instructions", auth_url=auth_url)
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
                            logger.info("google_drive.oauth_manual_success")

                    except Exception as e:
                        logger.exception("google_drive.oauth_error", error=str(e))
                        raise Exception(f"Authentication failed: {str(e)}. Please check your OAuth consent screen configuration.")
                
                # Save credentials for next run
                try:
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info("google_drive.credentials_saved")
                except Exception as e:
                    logger.warning(
                        "google_drive.credentials_save_failed",
                        error=str(e),
                    )
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("google_drive.service_initialized")
            
        except Exception as e:
            logger.exception("google_drive.authentication_fatal", error=str(e))
            raise Exception(f"Failed to authenticate with Google Drive: {str(e)}")
    
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
    
    def list_images(self, folder_id: str, max_retries: int = 3) -> List[Dict]:
        """
        List all image files in folder with retry logic
        
        Args:
            folder_id: Google Drive folder ID
            max_retries: Number of retry attempts for failed API calls
        
        Returns:
            List of image file dictionaries
        
        Raises:
            Exception: If listing fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # First, try to get folder info to check if we have access
                folder_info = self.service.files().get(fileId=folder_id).execute()
                logger.info(
                    "google_drive.folder_found",
                    folder_id=folder_id,
                    folder_name=folder_info.get('name'),
                )
                
                query = f"'{folder_id}' in parents and (mimeType contains 'image/')"
                
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name, mimeType, size)",
                    pageSize=1000
                ).execute()
                
                files = results.get('files', [])
                logger.info(
                    "google_drive.images_listed",
                    folder_id=folder_id,
                    count=len(files),
                )
                return files
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "google_drive.list_images_retry",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                else:
                    logger.error(
                        "google_drive.list_images_failed",
                        attempts=max_retries,
                        error=str(e),
                    )
        
        # If we get here, all retries failed
        error_msg = f"Cannot access folder after {max_retries} attempts. Please check: 1) Folder exists 2) You have access 3) Folder ID is correct. Error: {str(last_error)}"
        raise Exception(error_msg)
    
    def download_file(self, file_id: str, file_path: str, max_retries: int = 3):
        """
        Download file from Google Drive with retry logic
        
        Args:
            file_id: Google Drive file ID
            file_path: Local path to save the file
            max_retries: Number of retry attempts for failed downloads
        
        Raises:
            Exception: If download fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                request = self.service.files().get_media(fileId=file_id)
                
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                
                # Success - return immediately
                return
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "google_drive.download_retry",
                        attempt=attempt + 1,
                        file_id=file_id,
                        error=str(e),
                    )
                    # Clean up partial download
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                else:
                    logger.error(
                        "google_drive.download_failed",
                        attempts=max_retries,
                        file_id=file_id,
                    )
        
        # If we get here, all retries failed
        raise Exception(f"Failed to download file {file_id} after {max_retries} attempts: {str(last_error)}")
    
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
            
            logger.info(
                "google_drive.folder_created",
                folder_name=name,
                folder_id=folder.get('id'),
            )
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
            logger.info("google_drive.test_access_start")
            
            # List some folders in user's Drive
            results = self.service.files().list(
                q="mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name, parents)",
                pageSize=10
            ).execute()
            
            folders = results.get('files', [])
            logger.info("google_drive.test_access_result", folder_count=len(folders))
            for folder in folders:
                logger.debug(
                    "google_drive.test_access_folder",
                    folder_id=folder['id'],
                    folder_name=folder['name'],
                )
            
            return folders
            
        except Exception as e:
            logger.exception("google_drive.test_access_failed", error=str(e))
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
            
            logger.info(
                "google_drive.test_folder_created",
                folder_id=folder_id,
                folder_name=folder_name,
            )
            print(f"You can access it at: https://drive.google.com/drive/folders/{folder_id}")
            
            return folder_id
            
        except Exception as e:
            logger.exception("google_drive.test_folder_failed", error=str(e))
            raise
    
    def check_folder_permissions(self, folder_id: str, max_retries: int = 3) -> Dict[str, bool]:
        """
        Check what permissions we have on a folder with retry logic
        
        Args:
            folder_id: Google Drive folder ID
            max_retries: Number of retry attempts
        
        Returns:
            Dictionary with permission flags and folder name
        
        Raises:
            Exception: If permission check fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
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
                
                logger.info(
                    "google_drive.permissions_checked",
                    folder_id=folder_id,
                    permissions=permissions,
                )
                return permissions
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "google_drive.permissions_retry",
                        attempt=attempt + 1,
                        folder_id=folder_id,
                        error=str(e),
                    )
                else:
                    logger.error(
                        "google_drive.permissions_failed",
                        folder_id=folder_id,
                        attempts=max_retries,
                        error=str(e),
                    )
        
        # If we get here, all retries failed
        raise Exception(f"Cannot check folder permissions after {max_retries} attempts: {str(last_error)}")