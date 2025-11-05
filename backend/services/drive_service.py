"""
Service layer for Google Drive operations.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.logger import get_logger
from google_drive.google_drive import GoogleDriveAPI


logger = get_logger(__name__)


class DriveService:
    """
    Service for Google Drive authentication and file operations.
    
    This service provides a clean interface for all Google Drive
    interactions including authentication, file listing, downloads,
    and folder management.
    """
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize DriveService with Google Drive API.
        
        Args:
            credentials_file: Path to Google OAuth credentials file
        """
        self.drive_api = GoogleDriveAPI(credentials_file)
        logger.info("DriveService initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive.
        
        Returns:
            True if authentication successful
            
        Raises:
            Exception: If authentication fails
        """
        try:
            logger.info("Authenticating with Google Drive")
            self.drive_api.authenticate()
            logger.info("Google Drive authentication successful")
            return True
        except Exception as e:
            logger.error(f"Google Drive authentication failed: {str(e)}")
            raise
    
    def list_files_in_folder(
        self,
        folder_id: str,
        mime_type: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            mime_type: Optional MIME type filter (e.g., 'image/jpeg')
            max_results: Maximum number of results to return
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            logger.info(f"Listing files in folder: {folder_id}")
            files = self.drive_api.list_files(
                folder_id=folder_id,
                mime_type=mime_type,
                max_results=max_results
            )
            logger.info(f"Found {len(files)} file(s) in folder")
            return files
        except Exception as e:
            logger.error(f"Error listing files in folder {folder_id}: {str(e)}")
            raise
    
    def list_photos_in_folder(
        self,
        folder_id: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List photos (images) in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            max_results: Maximum number of results to return
            
        Returns:
            List of photo metadata dictionaries
        """
        try:
            logger.info(f"Listing photos in folder: {folder_id}")
            
            # Get files with image MIME types
            image_mime_types = [
                'image/jpeg',
                'image/jpg',
                'image/png',
                'image/gif',
                'image/bmp',
                'image/webp'
            ]
            
            all_photos = []
            for mime_type in image_mime_types:
                photos = self.list_files_in_folder(folder_id, mime_type, max_results)
                all_photos.extend(photos)
            
            # Remove duplicates based on file ID
            seen = set()
            unique_photos = []
            for photo in all_photos:
                if photo['id'] not in seen:
                    seen.add(photo['id'])
                    unique_photos.append(photo)
            
            logger.info(f"Found {len(unique_photos)} photo(s) in folder")
            return unique_photos
        except Exception as e:
            logger.error(f"Error listing photos in folder {folder_id}: {str(e)}")
            raise
    
    def download_file(
        self,
        file_id: str,
        destination_path: str
    ) -> str:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            destination_path: Local path to save the file
            
        Returns:
            Path to downloaded file
        """
        try:
            logger.info(f"Downloading file {file_id} to {destination_path}")
            downloaded_path = self.drive_api.download_file(file_id, destination_path)
            logger.info(f"File downloaded successfully")
            return downloaded_path
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            raise
    
    def upload_file(
        self,
        file_path: str,
        folder_id: str,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Local path to the file
            folder_id: Google Drive folder ID to upload to
            file_name: Optional name for the uploaded file
            
        Returns:
            Uploaded file metadata
        """
        try:
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"Uploading file {file_path} to folder {folder_id}")
            uploaded_file = self.drive_api.upload_file(file_path, folder_id, file_name)
            logger.info(f"File uploaded successfully: {uploaded_file.get('id')}")
            return uploaded_file
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {str(e)}")
            raise
    
    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: Optional parent folder ID
            
        Returns:
            Created folder metadata with ID
        """
        try:
            logger.info(f"Creating folder: {folder_name}")
            folder = self.drive_api.create_folder(folder_name, parent_folder_id)
            logger.info(f"Folder created successfully: {folder.get('id')}")
            return folder
        except Exception as e:
            logger.error(f"Error creating folder {folder_name}: {str(e)}")
            raise
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary
        """
        try:
            logger.debug(f"Getting metadata for file: {file_id}")
            metadata = self.drive_api.get_file_metadata(file_id)
            return metadata
        except Exception as e:
            logger.error(f"Error getting file metadata {file_id}: {str(e)}")
            raise
    
    def copy_file(
        self,
        file_id: str,
        destination_folder_id: str,
        new_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Copy a file to another folder in Google Drive.
        
        Args:
            file_id: Source file ID
            destination_folder_id: Destination folder ID
            new_name: Optional new name for the copied file
            
        Returns:
            Copied file metadata
        """
        try:
            logger.info(f"Copying file {file_id} to folder {destination_folder_id}")
            copied_file = self.drive_api.copy_file(file_id, destination_folder_id, new_name)
            logger.info(f"File copied successfully: {copied_file.get('id')}")
            return copied_file
        except Exception as e:
            logger.error(f"Error copying file {file_id}: {str(e)}")
            raise
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if deletion successful
        """
        try:
            logger.info(f"Deleting file: {file_id}")
            self.drive_api.delete_file(file_id)
            logger.info("File deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            raise
    
    def get_folder_name(self, folder_id: str) -> str:
        """
        Get folder name from folder ID.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Folder name
        """
        try:
            metadata = self.get_file_metadata(folder_id)
            return metadata.get('name', 'Unknown')
        except Exception as e:
            logger.error(f"Error getting folder name {folder_id}: {str(e)}")
            raise

