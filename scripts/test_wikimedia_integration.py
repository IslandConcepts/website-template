#!/usr/bin/env python3
"""
Test script for the Wikimedia Commons image search and download functionality

This script tests the ability to search Wikimedia Commons for celebrity images,
download them, upload to S3, and update the XML catalog.
"""

import os
import sys
import argparse
from pprint import pprint

# Add the scripts directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions to test
from image_urls import (
    extract_celebrity_name,
    search_wikimedia_commons,
    download_image,
    upload_to_s3,
    update_image_catalog,
    fetch_wikimedia_image,
    get_image_url_for_topic
)

def test_celebrity_extraction(celebrity_name):
    """Test the celebrity name extraction function"""
    print(f"=== Testing Celebrity Name Extraction for: '{celebrity_name}' ===")
    
    # Create a topic that includes the celebrity name
    topic = f"{celebrity_name} makes headlines with surprising announcement"
    
    # Extract the celebrity name
    extracted_name = extract_celebrity_name(topic)
    
    print(f"Topic: '{topic}'")
    print(f"Extracted celebrity name: {extracted_name}")
    
    if extracted_name and celebrity_name.lower() in extracted_name.lower():
        print("✓ SUCCESS: Celebrity name was correctly extracted")
    else:
        print("✗ FAILURE: Celebrity name was not correctly extracted")
    
    return extracted_name

def test_wikimedia_search(celebrity_name):
    """Test searching for a celebrity on Wikimedia Commons"""
    print(f"\n=== Testing Wikimedia Commons Search for: '{celebrity_name}' ===")
    
    # Search for the celebrity
    result = search_wikimedia_commons(celebrity_name)
    
    if result:
        print(f"✓ SUCCESS: Found image on Wikimedia Commons")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  Uploader: {result['user']}")
        print(f"  Dimensions: {result.get('width', 'Unknown')}x{result.get('height', 'Unknown')}")
        print(f"  License: {result.get('license', 'Unknown')}")
    else:
        print(f"✗ FAILURE: No image found on Wikimedia Commons for '{celebrity_name}'")
    
    return result

def test_image_download(image_url, output_path):
    """Test downloading an image from a URL"""
    print(f"\n=== Testing Image Download ===")
    print(f"URL: {image_url}")
    print(f"Output path: {output_path}")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Download the image
    success = download_image(image_url, output_path)
    
    if success:
        print(f"✓ SUCCESS: Image downloaded successfully to {output_path}")
        # Check if the file exists and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"  File size: {os.path.getsize(output_path)} bytes")
        else:
            print(f"  Warning: File doesn't exist or is empty")
    else:
        print(f"✗ FAILURE: Failed to download image")
    
    return success

def test_s3_upload(local_file, s3_key):
    """Test uploading an image to S3"""
    print(f"\n=== Testing S3 Upload ===")
    print(f"Local file: {local_file}")
    print(f"S3 key: {s3_key}")
    
    # Upload the image to S3
    success = upload_to_s3(local_file, s3_key)
    
    if success:
        print(f"✓ SUCCESS: Image uploaded to S3 as {s3_key}")
    else:
        print(f"✗ FAILURE: Failed to upload image to S3")
    
    return success

def test_catalog_update(image_filename):
    """Test updating the image catalog XML"""
    print(f"\n=== Testing Image Catalog Update ===")
    print(f"Image filename: {image_filename}")
    
    # Update the catalog
    success = update_image_catalog(image_filename, ["celebrities"])
    
    if success:
        print(f"✓ SUCCESS: Image catalog updated with {image_filename}")
    else:
        print(f"✗ FAILURE: Failed to update image catalog")
    
    return success

def test_complete_workflow(celebrity_name):
    """Test the complete workflow from topic to image URL"""
    print(f"\n=== Testing Complete Workflow for: '{celebrity_name}' ===")
    
    # Create a topic with a very unusual celebrity name that won't be in our database
    # This forces the system to use the Wikimedia fallback
    topic = f"{celebrity_name} surprises fans with unexpected announcement"
    print(f"Topic: '{topic}'")
    
    # Test direct fetch_wikimedia_image first (bypassing the normal flow)
    print("Testing direct Wikimedia fetch...")
    wiki_result = fetch_wikimedia_image(topic)
    
    if wiki_result:
        wiki_url, wiki_credit = wiki_result
        print(f"Direct Wikimedia fetch successful:")
        print(f"  URL: {wiki_url}")
        print(f"  Credit: {wiki_credit}")
        
        if "wikimedia.org" in wiki_url or "s3.amazonaws.com" in wiki_url:
            print("✓ SUCCESS: fetch_wikimedia_image returned valid URL")
        else:
            print("✗ FAILURE: Invalid URL returned from fetch_wikimedia_image")
    else:
        print("✗ FAILURE: fetch_wikimedia_image returned no result")
    
    return wiki_result

def test_fetch_wikimedia_image(celebrity_name):
    """Test the fetch_wikimedia_image function directly"""
    print(f"\n=== Testing fetch_wikimedia_image for: '{celebrity_name}' ===")
    
    # Create a topic
    topic = f"{celebrity_name} in the news"
    print(f"Topic: '{topic}'")
    
    # Fetch Wikimedia image
    result = fetch_wikimedia_image(topic)
    
    if result:
        image_url, credit = result
        print(f"✓ SUCCESS: Found image for {celebrity_name}")
        print(f"  URL: {image_url}")
        print(f"  Credit: {credit}")
        
        if "s3.amazonaws.com" in image_url:
            print("  (Image was uploaded to S3)")
        elif "wikimedia.org" in image_url:
            print("  (Using direct Wikimedia URL)")
    else:
        print(f"✗ FAILURE: No image found for {celebrity_name}")
    
    return result

def check_aws_credentials():
    """Check if AWS credentials are available"""
    from image_urls import AWS_ACCESS_KEY, AWS_SECRET_KEY
    
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        print(f"AWS credentials found: {AWS_ACCESS_KEY[:5]}...{AWS_ACCESS_KEY[-3:]}")
        return True
    else:
        print("Warning: AWS credentials not found. S3 uploads will fail.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Wikimedia Commons integration")
    parser.add_argument("--celebrity", type=str, default="Jamie Lee Curtis",
                        help="Celebrity name to use for testing")
    parser.add_argument("--complete", action="store_true",
                        help="Run the complete workflow test")
    parser.add_argument("--extract", action="store_true",
                        help="Test celebrity name extraction")
    parser.add_argument("--search", action="store_true", 
                        help="Test Wikimedia Commons search")
    parser.add_argument("--fetch", action="store_true",
                        help="Test fetch_wikimedia_image function")
    parser.add_argument("--download", action="store_true",
                        help="Test image download")
    parser.add_argument("--upload", action="store_true",
                        help="Test S3 upload")
    parser.add_argument("--catalog", action="store_true",
                        help="Test catalog update")
    
    args = parser.parse_args()
    
    # Check AWS credentials before running tests
    check_aws_credentials()
    
    if not any([args.complete, args.extract, args.search, args.fetch, 
                args.download, args.upload, args.catalog]):
        # If no specific tests are specified, run all tests
        args.complete = True
    
    if args.extract:
        test_celebrity_extraction(args.celebrity)
    
    if args.search:
        test_wikimedia_search(args.celebrity)
    
    if args.fetch:
        test_fetch_wikimedia_image(args.celebrity)
    
    if args.download or args.upload or args.catalog:
        # First search for an image
        search_result = search_wikimedia_commons(args.celebrity)
        if not search_result:
            print(f"No image found for {args.celebrity}, cannot test download/upload/catalog")
            return
        
        # Generate a test filename
        clean_name = args.celebrity.replace(" ", "_").lower()
        image_url = search_result["url"]
        ext = image_url.split(".")[-1]
        if ext not in ["jpg", "jpeg", "png", "gif"]:
            ext = "jpg"
        
        # Create a filename for testing
        test_filename = f"{clean_name}_test_image.{ext}"
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        test_path = os.path.join(temp_dir, test_filename)
        
        # Test download if requested
        if args.download:
            download_success = test_image_download(image_url, test_path)
            if not download_success:
                print("Download failed, cannot test upload/catalog")
                return
        
        # Test upload if requested
        if args.upload:
            if not os.path.exists(test_path):
                # Download the image first if it doesn't exist
                download_success = test_image_download(image_url, test_path)
                if not download_success:
                    print("Download failed, cannot test upload")
                    return
            
            upload_success = test_s3_upload(test_path, test_filename)
            if not upload_success:
                print("Upload failed, cannot test catalog update")
                return
        
        # Test catalog update if requested
        if args.catalog:
            catalog_success = test_catalog_update(test_filename)
    
    if args.complete:
        # Test the complete workflow
        test_complete_workflow(args.celebrity)

if __name__ == "__main__":
    main()