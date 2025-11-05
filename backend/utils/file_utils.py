"""
File utility functions.
"""
from pathlib import Path
from typing import List
import os
import time

from core.logger import get_logger


logger = get_logger(__name__)


def ensure_directory(directory_path: str) -> Path:
    """
    Ensure a directory exists, create if it doesn't.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory exists: {directory_path}")
    return path


def cleanup_temp_files(directory: str, max_age_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified age.
    
    Args:
        directory: Directory to clean up
        max_age_hours: Maximum age of files to keep in hours
        
    Returns:
        Number of files deleted
    """
    try:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return 0
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old temp file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
        
        logger.info(f"Cleaned up {deleted_count} temp file(s) from {directory}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")
        return 0


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    return path.stat().st_size


def is_image_file(file_path: str) -> bool:
    """
    Check if a file is an image based on extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file is an image
    """
    image_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'
    }
    
    path = Path(file_path)
    return path.suffix.lower() in image_extensions


def get_files_by_extension(
    directory: str,
    extensions: List[str],
    recursive: bool = True
) -> List[Path]:
    """
    Get all files with specified extensions in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions (e.g., ['.jpg', '.png'])
        recursive: Whether to search recursively
        
    Returns:
        List of Path objects
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return []
    
    files = []
    extensions_lower = [ext.lower() for ext in extensions]
    
    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"
    
    for file_path in dir_path.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in extensions_lower:
            files.append(file_path)
    
    logger.debug(f"Found {len(files)} file(s) with extensions {extensions} in {directory}")
    return files


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    safe_name = safe_name.strip('. ')
    
    # Ensure filename is not empty
    if not safe_name:
        safe_name = "unnamed"
    
    return safe_name

