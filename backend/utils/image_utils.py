"""
Image processing utility functions.
"""
from pathlib import Path
from typing import Tuple, Optional
import cv2
import numpy as np

from core.logger import get_logger


logger = get_logger(__name__)


def resize_image(
    image_path: str,
    max_dimension: int = 1920,
    output_path: Optional[str] = None
) -> str:
    """
    Resize image to maximum dimension while maintaining aspect ratio.
    
    Args:
        image_path: Path to input image
        max_dimension: Maximum width or height
        output_path: Optional output path (overwrites input if not specified)
        
    Returns:
        Path to resized image
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        height, width = img.shape[:2]
        
        # Check if resizing is needed
        if height <= max_dimension and width <= max_dimension:
            logger.debug(f"Image already smaller than max dimension: {image_path}")
            return image_path
        
        # Calculate new dimensions
        if height > width:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        else:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        
        # Resize image
        resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Save resized image
        if output_path is None:
            output_path = image_path
        
        cv2.imwrite(output_path, resized)
        logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        
        return output_path
    except Exception as e:
        logger.error(f"Error resizing image {image_path}: {str(e)}")
        raise


def compress_image(
    image_path: str,
    quality: int = 85,
    output_path: Optional[str] = None
) -> str:
    """
    Compress image with specified quality.
    
    Args:
        image_path: Path to input image
        quality: JPEG quality (1-100)
        output_path: Optional output path (overwrites input if not specified)
        
    Returns:
        Path to compressed image
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        # Set output path
        if output_path is None:
            output_path = image_path
        
        # Compress and save
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        cv2.imwrite(output_path, img, encode_params)
        
        logger.info(f"Compressed image with quality {quality}: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error compressing image {image_path}: {str(e)}")
        raise


def generate_thumbnail(
    image_path: str,
    thumbnail_size: Tuple[int, int] = (200, 200),
    output_path: Optional[str] = None
) -> str:
    """
    Generate a thumbnail for an image.
    
    Args:
        image_path: Path to input image
        thumbnail_size: Thumbnail size (width, height)
        output_path: Optional output path (defaults to input_thumb.jpg)
        
    Returns:
        Path to thumbnail
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        # Generate thumbnail
        thumbnail = cv2.resize(img, thumbnail_size, interpolation=cv2.INTER_AREA)
        
        # Set output path
        if output_path is None:
            input_path = Path(image_path)
            output_path = str(input_path.parent / f"{input_path.stem}_thumb.jpg")
        
        # Save thumbnail
        cv2.imwrite(output_path, thumbnail)
        
        logger.info(f"Generated thumbnail: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating thumbnail for {image_path}: {str(e)}")
        raise


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """
    Get image dimensions without loading the full image.
    
    Args:
        image_path: Path to image
        
    Returns:
        Tuple of (width, height)
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        height, width = img.shape[:2]
        return (width, height)
    except Exception as e:
        logger.error(f"Error getting image dimensions: {str(e)}")
        raise


def is_valid_image(image_path: str) -> bool:
    """
    Check if file is a valid image.
    
    Args:
        image_path: Path to image
        
    Returns:
        True if valid image
    """
    try:
        img = cv2.imread(image_path)
        return img is not None
    except Exception:
        return False


def crop_image(
    image_path: str,
    x: int,
    y: int,
    width: int,
    height: int,
    output_path: Optional[str] = None
) -> str:
    """
    Crop image to specified region.
    
    Args:
        image_path: Path to input image
        x: Top-left x coordinate
        y: Top-left y coordinate
        width: Crop width
        height: Crop height
        output_path: Optional output path
        
    Returns:
        Path to cropped image
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        # Crop image
        cropped = img[y:y+height, x:x+width]
        
        # Set output path
        if output_path is None:
            input_path = Path(image_path)
            output_path = str(input_path.parent / f"{input_path.stem}_cropped{input_path.suffix}")
        
        # Save cropped image
        cv2.imwrite(output_path, cropped)
        
        logger.info(f"Cropped image to {width}x{height}: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error cropping image {image_path}: {str(e)}")
        raise

