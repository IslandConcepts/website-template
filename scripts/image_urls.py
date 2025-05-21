#!/usr/bin/env python3
"""
Image URL helpers for CringeWorthy content generation

This module provides functions to select appropriate images from the CringeWorthy S3 bucket,
with intelligent topic matching and integration with the XML image catalog.
"""

import os
import re
import random
import xml.etree.ElementTree as ET
from pathlib import Path

# S3 bucket base URL
S3_BASE_URL = "https://cringeworthy.s3.amazonaws.com/images/"

# Path to the XML image catalog
IMAGE_CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    "cringeworthy_images.xml"
)

# Category mapping for topic classification
CATEGORY_MAP = {
    "true_crime": ["crime", "murder", "criminal", "theft", "robbery", "killer", "police", "investigation"],
    "politics": ["government", "election", "president", "democracy", "congress", "politician", "senator"],
    "social_media": ["instagram", "twitter", "facebook", "tiktok", "social", "viral", "influencer", "follower"],
    "workplace": ["office", "job", "corporate", "work", "business", "employee", "boss", "coworker"],
    "cringe": ["embarrassing", "awkward", "uncomfortable", "weird", "fail", "embarrassment", "humiliation"],
    "family": ["home", "parents", "children", "relatives", "domestic", "family", "dad", "mom", "son", "daughter"],
    "education": ["school", "college", "university", "student", "academic", "classroom", "teacher", "professor"],
    "horror": ["scary", "creepy", "disturbing", "paranormal", "ghost", "monster", "haunted", "supernatural"],
    "technology": ["tech", "digital", "computer", "gadget", "internet", "app", "software", "hardware"],
    "celebrities": ["famous", "star", "celebrity", "hollywood", "actor", "actress", "singer", "performer"],
    "animals": ["animal", "pet", "wildlife", "dog", "cat", "bird", "zoo", "exotic"],
    "food": ["meal", "restaurant", "cooking", "chef", "recipe", "kitchen", "dining", "breakfast", "lunch", "dinner"]
}

# Fallback sample images if XML parsing fails
FALLBACK_IMAGES = {
    "politics": [
        "politics/American_flag_001.jpg",
        "politics/Congress_002.jpg",
        "politics/President_003.jpg"
    ],
    "true_crime": [
        "crime/Police_tape_001.jpg",
        "crime/Handcuffs_002.jpg",
        "crime/Courtroom_003.jpg"
    ],
    "cringe": [
        "cringe/Awkward_001.jpg",
        "cringe/Embarrassed_002.jpg",
        "cringe/Fail_003.jpg"
    ],
    "default": [
        "default/Default_001.jpg",
        "default/Default_002.jpg",
        "default/Default_003.jpg"
    ]
}

def load_images_from_xml():
    """
    Load available images from the XML catalog
    
    Returns:
        dict: A dictionary of category -> list of image filenames
    """
    try:
        # Check if catalog exists
        if not os.path.exists(IMAGE_CATALOG_PATH):
            print(f"Warning: Image catalog not found at {IMAGE_CATALOG_PATH}")
            return {}
            
        # Read file content
        with open(IMAGE_CATALOG_PATH, 'r') as f:
            content = f.read()

        # The XML file doesn't have a root element, so we need to add one
        if not content.startswith('<?xml') and not content.startswith('<root>'):
            content = '<root>' + content + '</root>'
            
        # Parse XML content
        image_data = {}
        
        # Use a simple regex to extract image tags since the file isn't proper XML
        image_matches = re.findall(r'<image>([^<]+)</image>', content)
        
        for image_filename in image_matches:
            image_filename = image_filename.strip()
            
            # Extract categories from filename
            categories = []
            for category in CATEGORY_MAP:
                if category.lower() in image_filename.lower():
                    categories.append(category)
            
            # Extract image keywords from filename (words separated by _ or in metadata)
            keywords = re.findall(r'([a-zA-Z0-9]+)', image_filename)
            
            # Add image to all relevant categories
            for category in categories or ["default"]:
                if category not in image_data:
                    image_data[category] = []
                image_data[category].append({
                    "filename": image_filename,
                    "keywords": keywords,
                    "credit": extract_credit_from_filename(image_filename)
                })
        
        print(f"Loaded {len(image_matches)} images from XML catalog")
        return image_data
    
    except Exception as e:
        print(f"Error loading images from XML: {e}")
        return {}

def extract_credit_from_filename(filename):
    """
    Extract the photo credit from the filename
    
    Args:
        filename: The image filename
        
    Returns:
        str: The photo credit
    """
    # Look for credit pattern: name_by.jpg or name_by-sa.jpg
    credit_match = re.search(r'_([^_]+)_by(-[a-z]+)?\.', filename)
    if credit_match:
        credit = credit_match.group(1).replace('_', ' ')
        return credit
    
    # Fallback credits
    sample_credits = [
        "CringeWorthy Staff",
        "Alice Johnson",
        "Michael Chen"
    ]
    return random.choice(sample_credits)

def get_image_url_for_topic(topic):
    """
    Get a relevant image URL for a given topic
    
    Args:
        topic: The topic to get an image for
        
    Returns:
        tuple: (image_url, image_credit)
    """
    # Load images from XML catalog
    all_images = load_images_from_xml()
    
    # Convert topic to lowercase for matching
    topic_lower = topic.lower().replace(" ", "_")
    
    # Find the most appropriate category
    best_category = "default"
    matched_keywords = 0
    topic_words = set(re.findall(r'([a-zA-Z0-9]+)', topic_lower))
    
    for category, keywords in CATEGORY_MAP.items():
        # Check if topic directly mentions the category
        if category.lower() in topic_lower:
            best_category = category
            break
        
        # Otherwise count keyword matches
        category_matches = sum(1 for kw in keywords if kw in topic_lower)
        if category_matches > matched_keywords:
            matched_keywords = category_matches
            best_category = category
    
    # Find images in the best category or default to fallback
    if best_category in all_images and all_images[best_category]:
        # Sort images by keyword relevance to topic
        relevant_images = all_images[best_category]
        for image in relevant_images:
            image['relevance'] = sum(1 for kw in image['keywords'] if kw.lower() in topic_words)
        
        # Sort by relevance and select
        relevant_images.sort(key=lambda x: x['relevance'], reverse=True)
        selected_image = relevant_images[0] if relevant_images[0]['relevance'] > 0 else random.choice(relevant_images)
        
        # Build full URL and get credit
        image_url = S3_BASE_URL + selected_image['filename']
        image_credit = selected_image['credit']
    else:
        # Use fallback images
        if best_category in FALLBACK_IMAGES:
            fallback_category = best_category
        else:
            fallback_category = "default"
            
        image_filename = random.choice(FALLBACK_IMAGES[fallback_category])
        image_url = S3_BASE_URL + image_filename
        image_credit = extract_credit_from_filename(image_filename) or "CringeWorthy Staff"
    
    print(f"Selected image for topic '{topic}': {image_url}")
    return (image_url, image_credit)

# Cache for XML catalog to avoid repeated parsing
_image_catalog_cache = None

def get_cached_image_catalog():
    """
    Get the image catalog, using a cached version if available
    
    Returns:
        dict: The image catalog
    """
    global _image_catalog_cache
    if _image_catalog_cache is None:
        _image_catalog_cache = load_images_from_xml()
    return _image_catalog_cache