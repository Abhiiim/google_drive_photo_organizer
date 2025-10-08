#!/usr/bin/env python3
"""
Check permissions on a specific Google Drive folder
"""

from backend.google_drive.google_drive import GoogleDriveClient
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_permissions.py <folder_id_or_link>")
        print("Example: python check_permissions.py 1ABC123XYZ789")
        return
    
    folder_input = sys.argv[1]
    
    try:
        client = GoogleDriveClient()
        
        # Extract folder ID if it's a link
        if 'drive.google.com' in folder_input:
            folder_id = client.extract_folder_id(folder_input)
        else:
            folder_id = folder_input
        
        print(f"Checking permissions for folder ID: {folder_id}")
        print("=" * 50)
        
        permissions = client.check_folder_permissions(folder_id)
        
        print(f"Folder Name: {permissions['folder_name']}")
        print(f"Can Read: {'✅' if permissions['can_read'] else '❌'}")
        print(f"Can Create Folders: {'✅' if permissions['can_create_folders'] else '❌'}")
        print(f"Can Edit: {'✅' if permissions['can_edit'] else '❌'}")
        
        if permissions['can_create_folders']:
            print("\n✅ This folder can be used with the Face Organizer!")
        else:
            print("\n❌ This folder cannot be used - you need Editor permissions!")
            print("Ask the folder owner to give you Editor access.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()