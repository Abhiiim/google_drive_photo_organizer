#!/usr/bin/env python3
"""
Test script to verify multi-face detection is working properly
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from face_detector.face_detector import FaceDetector
from photo_organizer.photo_organizer import PhotoOrganizer

def test_face_detection():
    """Test face detection on sample images"""
    print("🧪 Testing Face Detection System")
    print("=" * 50)
    
    # Initialize face detector
    detector = FaceDetector(min_face_size=30, quality_threshold=0.2)
    
    # Test with a sample image (you'll need to provide your own test images)
    test_images_dir = Path("test_images")
    
    if not test_images_dir.exists():
        print("❌ Test images directory not found!")
        print("Please create a 'test_images' folder and add some sample photos:")
        print("  - single_face.jpg (photo with one person)")
        print("  - multi_face.jpg (photo with multiple people)")
        print("  - group_photo.jpg (photo with many people)")
        return
    
    # Test each image in the test directory
    for image_path in test_images_dir.glob("*.jpg"):
        print(f"\n🖼️  Testing: {image_path.name}")
        print("-" * 30)
        
        faces, embeddings = detector.detect_and_extract_faces(image_path)
        
        print(f"Results:")
        print(f"  - Raw faces detected: {len(faces)}")
        print(f"  - Valid faces with embeddings: {len(embeddings)}")
        
        if len(embeddings) == 0:
            print("  ⚠️  No faces detected - try lowering quality_threshold")
        elif len(embeddings) == 1:
            print("  ✅ Single face detected")
        else:
            print(f"  🎉 Multiple faces detected: {len(embeddings)} faces")

def test_photo_organizer():
    """Test the complete photo organization system"""
    print("\n🗂️  Testing Photo Organization System")
    print("=" * 50)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Initialize organizer
        organizer = PhotoOrganizer(distance_threshold=0.6)
        organizer.output_dir = Path(temp_dir) / "organized_photos"
        
        # Mock some test data (you would normally use real Google Drive data)
        test_images = [
            {"name": "single_person.jpg", "id": "test1"},
            {"name": "group_photo.jpg", "id": "test2"},
            {"name": "family_photo.jpg", "id": "test3"}
        ]
        
        print("This would test the full organization process with Google Drive.")
        print("For a complete test, you need to:")
        print("1. Set up Google Drive credentials")
        print("2. Create a test folder with various photos")
        print("3. Run the actual organize_folder method")

if __name__ == "__main__":
    print("🚀 Multi-Face Detection Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Face Detection
        test_face_detection()
        
        # Test 2: Photo Organization (mock test)
        test_photo_organizer()
        
        print("\n✅ Test suite completed!")
        print("\nTo test with real data:")
        print("1. Add test images to 'test_images/' folder")
        print("2. Set up Google Drive credentials")
        print("3. Use the web interface to test with a real folder")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()