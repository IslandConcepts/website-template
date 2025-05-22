#!/usr/bin/env python3
"""
Test script for S3 upload functionality

This script tests uploading an image to S3 and updating the XML catalog.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the scripts directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from image_urls.py
from image_urls import upload_to_s3, download_image, update_image_catalog, fetch_wikimedia_image

def test_s3_credentials():
    """Test if AWS credentials are properly set up"""
    # Check if credentials are set in environment variables
    from image_urls import AWS_ACCESS_KEY, AWS_SECRET_KEY
    
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        print(f"AWS credentials found: {AWS_ACCESS_KEY[:5]}...{AWS_ACCESS_KEY[-3:]}")
        return True
    else:
        print("AWS credentials not found. Please set environment variables:")
        print("  source .env/aws-credentials.sh")
        print("Or manually export:")
        print("  export AWS_ACCESS_KEY_ID=your_access_key")
        print("  export AWS_SECRET_ACCESS_KEY=your_secret_key")
        return False

def test_wikimedia_integration(celebrity_name):
    """Test the complete Wikimedia integration with S3 upload"""
    # Create a topic with the celebrity name
    topic = f"{celebrity_name} makes surprising announcement"
    
    print(f"Testing Wikimedia integration for topic: '{topic}'")
    
    # Use fetch_wikimedia_image to get an image URL
    result = fetch_wikimedia_image(topic)
    
    if result:
        image_url, credit = result
        print(f"Image URL: {image_url}")
        print(f"Credit: {credit}")
        
        if "s3.amazonaws.com" in image_url:
            print("SUCCESS: Image was uploaded to S3")
            return True
        elif "wikimedia.org" in image_url:
            print("WARNING: Using direct Wikimedia URL (S3 upload failed or skipped)")
            return False
    else:
        print(f"No image found for {celebrity_name}")
    
    return False

def main():
    parser = argparse.ArgumentParser(description="Test S3 upload functionality")
    parser.add_argument("--celebrity", type=str, default="Pedro Pascal",
                        help="Celebrity name to use for testing")
    
    args = parser.parse_args()
    
    # Set up AWS credentials
    if not test_s3_credentials():
        print("Exiting due to credential setup failure")
        sys.exit(1)
    
    # Test the complete Wikimedia integration
    test_wikimedia_integration(args.celebrity)

if __name__ == "__main__":
    main()