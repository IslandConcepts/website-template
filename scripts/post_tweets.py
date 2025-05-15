#!/usr/bin/env python3
import os
import sys
import re
import time
import json
import random
import tweepy
import logging
import argparse
import difflib
import requests
from datetime import datetime, timezone, timedelta
# Updated to work with atproto 0.0.61
from atproto import Client as AtprotoClient
from pathlib import Path

# Try to import metrics tracker
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from tweet_metrics import get_metrics_tracker
    METRICS_ENABLED = True
except (ImportError, NameError) as e:
    print(f"Tweet metrics module not found, metrics tracking disabled: {e}")
    METRICS_ENABLED = False

# Try to load environment variables from .env file for local development
try:
    from dotenv import load_dotenv
    from pathlib import Path
    
    # First try the .env file in the project root
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment variables from: {env_path}")
    else:
        # Fall back to .env file in the scripts directory
        env_path = Path(__file__).resolve().parent / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"Loaded environment variables from: {env_path}")
        else:
            print("No .env file found, using system environment variables")
except ImportError:
    print("dotenv not installed, using system environment variables")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../logs/social_posting.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('social_posting')

# Ensure logs directory exists
Path(os.path.join(os.path.dirname(__file__), '../logs')).mkdir(exist_ok=True)

# Twitter API credentials (X)
X_API_KEY = os.environ.get('X_API_KEY')
X_API_SECRET = os.environ.get('X_API_SECRET')
X_ACCESS_TOKEN = os.environ.get('X_ACCESS_TOKEN')
X_ACCESS_SECRET = os.environ.get('X_ACCESS_SECRET')
X_BEARER_TOKEN = os.environ.get('X_BEARER_TOKEN')

# Bluesky API credentials
BLUESKY_USERNAME = os.environ.get('BLUESKY_USERNAME')
BLUESKY_PASSWORD = os.environ.get('BLUESKY_PASSWORD')

# Define the tweets directory
TWEETS_DIR = os.path.join(os.path.dirname(__file__), '../tweets')

# Define URL shortening configuration
# This needs to be global so it can be modified by command line arguments
global USE_URL_SHORTENER
USE_URL_SHORTENER = True

def load_tweets(platform="x"):
    """
    Loads tweets from daily tweet file or falls back to platform-specific files.
    Returns a list of all tweets.
    """
    try:
        # First try to use the new shared daily file
        today_date = datetime.now().strftime("%Y%m%d")
        daily_tweet_file = os.path.join(TWEETS_DIR, f"tweets_{today_date}.txt")
        
        if os.path.exists(daily_tweet_file):
            # Load from the daily tweet file
            logger.info(f"Loading tweets from daily file: {daily_tweet_file}")
            with open(daily_tweet_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by the separator (---) and filter out empty entries
            daily_tweets = [tweet.strip() for tweet in content.split('---') if tweet.strip()]
            logger.info(f"Loaded {len(daily_tweets)} tweets from daily file")
            return daily_tweets
        
        # Fallback to platform-specific files
        logger.info(f"Daily tweet file not found, falling back to platform-specific files")
        tweet_files = [f for f in os.listdir(TWEETS_DIR) if f.startswith(f"{platform}_tweets_") and f.endswith(".txt")]
        
        if not tweet_files:
            logger.error(f"No tweet files found for platform: {platform}")
            return []
        
        # Get today's date prefix
        today_prefix = datetime.now().strftime("%Y%m%d")
        
        # Filter for today's tweet files and sort by timestamp (most recent first)
        today_files = [f for f in tweet_files if today_prefix in f]
        today_files.sort(reverse=True)
        
        # If no today files, use the most recent ones from any day
        if not today_files:
            tweet_files.sort(reverse=True)
            files_to_use = tweet_files[:5]  # Use the 5 most recent files
        else:
            files_to_use = today_files
        
        # Load tweets from multiple files
        all_tweets = []
        for file_name in files_to_use:
            file_path = os.path.join(TWEETS_DIR, file_name)
            logger.info(f"Loading tweets from {file_path}")
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by the separator (---) and filter out empty entries
            file_tweets = [tweet.strip() for tweet in content.split('---') if tweet.strip()]
            
            # Add to all tweets
            all_tweets.extend(file_tweets)
            logger.info(f"Loaded {len(file_tweets)} tweets from {file_name}")
        
        logger.info(f"Loaded {len(all_tweets)} tweets total from {len(files_to_use)} files")
        return all_tweets
        
    except Exception as e:
        logger.error(f"Error loading tweets: {e}")
        return []

def load_recently_posted_tweets(platform, days=7):
    """
    Loads tweets that have been posted in the last specified days.
    This helps detect similarity with recently posted content.
    
    Loads from multiple sources:
    1. The permanent archive file (most reliable, contains ALL tweets)
    2. Recent daily history files (contains tweets posted on specific days)
    3. Recent tweet files (contains all available tweets, posted or not)
    
    Returns a comprehensive list of all tweets for duplicate detection.
    """
    recent_tweets = []
    archived_count = 0
    daily_count = 0
    file_count = 0
    
    try:
        # STEP 1: Load from the permanent archive file (most comprehensive source)
        archive_file = os.path.join(TWEETS_DIR, f"{platform}_posted_tweets_archive.txt")
        if os.path.exists(archive_file):
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split by the separator and filter out empty entries
                archived_tweets = [tweet.strip() for tweet in content.split('---') if tweet.strip()]
                
                # Extract the actual tweet text (remove the timestamp prefix if present)
                for tweet in archived_tweets:
                    # If the tweet has our timestamp format, extract just the tweet text
                    if '] ' in tweet:
                        tweet_text = tweet.split('] ', 1)[1].strip()
                    else:
                        tweet_text = tweet.strip()
                    
                    if tweet_text and tweet_text not in recent_tweets:
                        recent_tweets.append(tweet_text)
                        archived_count += 1
                
                logger.info(f"Loaded {archived_count} unique tweets from archive file")
            except Exception as e:
                logger.error(f"Error reading tweets from archive file: {e}")
        else:
            # If the archive file doesn't exist, create it
            logger.info(f"Archive file {archive_file} doesn't exist yet - will be created when tweets are posted")
        
        # STEP 2: Load from recent daily history files
        # Get date strings for the last N days
        date_strings = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            date_strings.append(date)
        
        # Look for posted tweet history files from the last N days
        fallback_tweets = []
        for date_str in date_strings:
            history_file = os.path.join(TWEETS_DIR, f"{platform}_posted_{date_str}.json")
            if os.path.exists(history_file):
                logger.info(f"Found posted tweet history for {date_str}")
                
                # Find corresponding tweet files from that day
                matching_tweet_files = [f for f in os.listdir(TWEETS_DIR) 
                                       if f.startswith(f"{platform}_tweets_") 
                                       and date_str in f 
                                       and f.endswith(".txt")]
                
                for tweet_file in matching_tweet_files:
                    file_path = os.path.join(TWEETS_DIR, tweet_file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Split by the separator (---) and filter out empty entries
                        file_tweets = [tweet.strip() for tweet in content.split('---') if tweet.strip()]
                        
                        # Load the posted indices
                        with open(history_file, 'r', encoding='utf-8') as f:
                            posted_indices = json.load(f)
                        
                        # Add the tweets that were posted (if index is valid)
                        for idx in posted_indices:
                            if 0 <= idx < len(file_tweets):
                                tweet_text = file_tweets[idx]
                                if tweet_text and tweet_text not in recent_tweets and tweet_text not in fallback_tweets:
                                    fallback_tweets.append(tweet_text)
                                    daily_count += 1
                    except Exception as e:
                        logger.error(f"Error reading tweets from {tweet_file}: {e}")
        
        if daily_count > 0:
            logger.info(f"Loaded {daily_count} additional unique tweets from daily history files")
        
        # STEP 3: As a final safety check, load recent tweet files (last 5) to ensure we don't miss anything
        try:
            # Get all tweet files for this platform
            all_tweet_files = sorted([f for f in os.listdir(TWEETS_DIR) 
                                if f.startswith(f"{platform}_tweets_") 
                                and f.endswith(".txt")], reverse=True)
            
            # Use only the 5 most recent files
            recent_files = all_tweet_files[:5]
            
            # Load tweets from these files
            additional_tweets = []
            for file in recent_files:
                file_path = os.path.join(TWEETS_DIR, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Split by the separator and filter out empty entries
                    if '---' in content:
                        file_tweets = [tweet.strip() for tweet in content.split('---') if tweet.strip()]
                    else:
                        file_tweets = [line.strip() for line in content.splitlines() if line.strip()]
                    
                    # Add unique tweets
                    for tweet in file_tweets:
                        if tweet and tweet not in recent_tweets and tweet not in fallback_tweets and tweet not in additional_tweets:
                            additional_tweets.append(tweet)
                            file_count += 1
                except Exception as e:
                    logger.error(f"Error reading tweets from {file}: {e}")
            
            if file_count > 0:
                logger.info(f"Loaded {file_count} additional unique tweets from recent tweet files")
        except Exception as e:
            logger.error(f"Error reading from recent tweet files: {e}")
        
        # Combine all sources, ensuring uniqueness
        all_tweets = recent_tweets + fallback_tweets
        
        # Log detailed stats about what we loaded
        logger.info(f"Total unique tweets loaded for similarity checking: {len(all_tweets)}")
        logger.info(f"Sources: Archive={archived_count}, Daily files={daily_count}, Recent files={file_count}")
        
        return all_tweets
        
    except Exception as e:
        logger.error(f"Error loading recent tweets: {e}")
        return []

def is_similar_to_existing(tweet, existing_tweets, similarity_threshold=0.7):
    """
    Checks if a tweet is too similar to any existing tweet.
    Returns True if similar, False otherwise.
    
    Uses difflib's SequenceMatcher to calculate text similarity.
    
    Enhanced to detect duplicates by:
    1. Using word-based similarity checking (better for detecting paraphrased content)
    2. Checking both the beginning and full content of tweets
    3. Applying stricter checks for tweets with similar beginnings
    4. Special handling for tweets containing URLs
    """
    if not existing_tweets:
        return False
    
    # Normalize tweet for comparison (lowercase, remove URLs and hashtags)
    def normalize_text(text):
        # Extract just the tweet text if it has a timestamp
        if '] ' in text:
            text = text.split('] ', 1)[1]
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        # Remove timestamps and random numbers that might be added
        text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
        # Convert to lowercase and strip whitespace
        return text.lower().strip()
    
    # Check if tweet contains a URL - treat it differently
    has_url = bool(re.search(r'https?://\S+', tweet))
    
    # Extract the URL(s) from the tweet
    urls = re.findall(r'https?://\S+', tweet) if has_url else []
    
    # Handle tweets with URLs specially
    if has_url:
        # For tweets with URLs, we want to avoid posting the same link with different text
        # Extract the URL domain for comparison
        domains = []
        for url in urls:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                if domain:
                    domains.append(domain)
            except Exception as e:
                logger.error(f"Error parsing URL {url}: {e}")
        
        # If we have domains, check for duplicates with the same domain
        if domains:
            # Look for existing tweets with the same domains
            for existing in existing_tweets:
                existing_urls = re.findall(r'https?://\S+', existing)
                
                for existing_url in existing_urls:
                    try:
                        from urllib.parse import urlparse
                        existing_domain = urlparse(existing_url).netloc
                        
                        # If we found a matching domain
                        if existing_domain in domains:
                            # Now check if the path is similar too
                            for url in urls:
                                url_path = urlparse(url).path
                                existing_path = urlparse(existing_url).path
                                
                                # If we're posting the same exact URL
                                if url_path == existing_path:
                                    logger.warning(f"Duplicate URL detected: {url}")
                                    logger.warning(f"Existing: {existing_url}")
                                    logger.warning(f"New: {url}")
                                    return True
                    except Exception as e:
                        logger.error(f"Error comparing URLs: {e}")
    
    normalized_tweet = normalize_text(tweet)
    
    # Skip very short tweets for similarity detection
    if len(normalized_tweet) < 20:
        return False
    
    # Extract first few words for checking similar beginnings
    words = normalized_tweet.split()
    beginning_words = words[:5]  # Use first 5 words
    beginning_phrase = ' '.join(beginning_words)
    
    for existing in existing_tweets:
        normalized_existing = normalize_text(existing)
        
        # Skip comparison with very short existing tweets
        if len(normalized_existing) < 20:
            continue
        
        # First check for similar beginnings (highly indicative of duplicate content)
        existing_words = normalized_existing.split()
        existing_beginning_words = existing_words[:5]
        existing_beginning_phrase = ' '.join(existing_beginning_words)
        
        # If beginnings are very similar, apply a stricter similarity check
        beginning_similarity = 0
        if len(beginning_words) >= 3 and len(existing_beginning_words) >= 3:
            beginning_similarity = difflib.SequenceMatcher(None, beginning_phrase, existing_beginning_phrase).ratio()
            
            # If first 5 words are extremely similar (> 0.9), highly likely to be duplicate content
            if beginning_similarity >= 0.9:
                logger.warning(f"Tweet beginning is {beginning_similarity:.2f} similar to existing tweet")
                logger.warning(f"New beginning: '{beginning_phrase}'")
                logger.warning(f"Existing beginning: '{existing_beginning_phrase}'")
                return True
        
        # For full content comparison, do different comparisons
        # 1. Full content similarity
        full_similarity = difflib.SequenceMatcher(None, normalized_tweet, normalized_existing).ratio()
        
        # 2. Word-set similarity (Jaccard similarity - how many words are the same)
        tweet_words = set(normalized_tweet.split())
        existing_words = set(normalized_existing.split())
        if tweet_words and existing_words:
            intersection = tweet_words.intersection(existing_words)
            union = tweet_words.union(existing_words)
            word_similarity = len(intersection) / len(union) if union else 0
        else:
            word_similarity = 0
            
        # Calculate combined score with more weight on beginning similarity
        combined_score = (full_similarity * 0.5) + (beginning_similarity * 0.3) + (word_similarity * 0.2)
        
        # Adjust threshold based on how similar the beginnings are
        # More similar beginnings = lower threshold to detect duplicates
        adjusted_threshold = similarity_threshold
        if beginning_similarity >= 0.7:
            # Lower the threshold the more similar the beginnings are
            adjusted_threshold = max(0.5, similarity_threshold - (beginning_similarity - 0.7))
            
        # Determine if this is a duplicate based on our scores
        is_duplicate = False
        
        # Very high full similarity is always a duplicate
        if full_similarity >= 0.9:
            is_duplicate = True
            logger.warning(f"Tweet content is {full_similarity:.2f} similar to existing tweet (exact match)")
            
        # High combined score with somewhat similar beginning is a duplicate
        elif combined_score >= adjusted_threshold and beginning_similarity >= 0.5:
            is_duplicate = True
            logger.warning(f"Tweet has combined similarity of {combined_score:.2f} with beginning similarity {beginning_similarity:.2f}")
            
        # High word similarity with somewhat similar beginning is a duplicate
        elif word_similarity >= 0.8 and beginning_similarity >= 0.5:
            is_duplicate = True
            logger.warning(f"Tweet has word similarity of {word_similarity:.2f} with beginning similarity {beginning_similarity:.2f}")
            
        # Log the result for debugging
        if is_duplicate:
            logger.warning(f"Duplicate detected:")
            logger.warning(f"New: {normalized_tweet[:60]}...")
            logger.warning(f"Old: {normalized_existing[:60]}...")
            logger.warning(f"Similarity metrics: full={full_similarity:.2f}, beginning={beginning_similarity:.2f}, word={word_similarity:.2f}")
            return True
        elif full_similarity >= 0.7 or combined_score >= 0.7:  # Log high similarity but don't reject
            logger.info(f"Tweet has high similarity (full={full_similarity:.2f}, combined={combined_score:.2f}) but below threshold - allowing it")
    
    return False

def save_used_tweet_ids(platform, tweet_ids, tweets=None):
    """
    Saves used tweet IDs to avoid reposting.
    Also archives the actual tweet text for better similarity checking.
    
    Args:
        platform: The platform (x, bluesky)
        tweet_ids: List of indices of the tweets that were posted
        tweets: Optional list of the actual tweet texts (if available)
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    history_file = os.path.join(TWEETS_DIR, f"{platform}_posted_{timestamp}.json")
    archive_file = os.path.join(TWEETS_DIR, f"{platform}_posted_tweets_archive.txt")
    
    try:
        # Load existing history if it exists
        existing_ids = []
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                existing_ids = json.load(f)
                
        # Add new IDs
        combined_ids = list(set(existing_ids + tweet_ids))
        
        # Save back to file
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(combined_ids, f)
            
        logger.info(f"Saved {len(combined_ids)} used tweet IDs to {history_file}")
        
        # If we have the actual tweet texts, archive them for future similarity checking
        if tweets and len(tweets) > 0:
            # Create the archive file if it doesn't exist
            if not os.path.exists(archive_file):
                logger.info(f"Creating new archive file: {archive_file}")
                os.makedirs(os.path.dirname(archive_file), exist_ok=True)
                
            # Load existing archive to check for duplicates
            existing_archive_tweets = []
            try:
                if os.path.exists(archive_file):
                    with open(archive_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        existing_archive_tweets = [t.strip() for t in content.split('---') if t.strip()]
                        logger.info(f"Loaded {len(existing_archive_tweets)} existing archived tweets")
            except Exception as e:
                logger.error(f"Error reading existing archive: {e}")
            
            # Normalize tweets for comparison
            def normalize_text(text):
                # Extract just the tweet text if it has a timestamp
                if '] ' in text:
                    text = text.split('] ', 1)[1]
                # Remove URLs
                text = re.sub(r'https?://\S+', '', text)
                # Remove hashtags
                text = re.sub(r'#\w+', '', text)
                # Remove timestamps and random numbers
                text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
                # Convert to lowercase and strip whitespace
                return text.lower().strip()
                
            # Normalize existing archive tweets
            normalized_existing = [normalize_text(t) for t in existing_archive_tweets]
            
            # Archive new tweets that aren't already in the archive
            new_archived = 0
            with open(archive_file, 'a', encoding='utf-8') as f:
                for tweet in tweets:
                    # Check if this tweet is already in the archive
                    normalized_tweet = normalize_text(tweet)
                    
                    # Skip very short tweets for comparison
                    if len(normalized_tweet) < 20:
                        # Just add it without checking
                        archive_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {tweet}\n---\n"
                        f.write(archive_entry)
                        new_archived += 1
                        continue
                    
                    # Check against existing archived tweets
                    is_duplicate = False
                    for existing in normalized_existing:
                        # Skip very short existing tweets
                        if len(existing) < 20:
                            continue
                            
                        # Calculate similarity using sequence matcher
                        import difflib
                        similarity = difflib.SequenceMatcher(None, normalized_tweet, existing).ratio()
                        
                        # If similarity is too high, consider it a duplicate
                        if similarity >= 0.9:
                            logger.warning(f"Tweet already in archive (similarity: {similarity:.2f})")
                            logger.warning(f"New: {normalized_tweet[:40]}...")
                            logger.warning(f"Existing: {existing[:40]}...")
                            is_duplicate = True
                            break
                    
                    # If not a duplicate, add to archive
                    if not is_duplicate:
                        archive_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {tweet}\n---\n"
                        f.write(archive_entry)
                        new_archived += 1
                        # Also add to our in-memory list for checking remaining tweets
                        normalized_existing.append(normalized_tweet)
                    else:
                        logger.warning(f"Skipping duplicate tweet in archive")
                    
            logger.info(f"Archived {new_archived} new unique tweet texts to {archive_file}")
        
    except Exception as e:
        logger.error(f"Error saving used tweet IDs: {e}")

def post_to_twitter(tweet_text):
    """
    Posts a tweet to Twitter/X using the v2 API, which works with the free tier.
    Returns True if successful, False otherwise.
    
    The tweet text will have its URLs shortened automatically if URL shortening is enabled.
    """
    # Shorten URLs in the tweet text to save characters
    tweet_text = shorten_urls_in_text(tweet_text)
    # Debug logging for environment variable content
    logger.info("======== TWITTER API CREDENTIALS DIAGNOSTICS ========")
    logger.info(f"OS Environment Variables:")
    import os
    env_vars = {k: v for k, v in os.environ.items() if k.startswith('X_')}
    logger.info(f"Found {len(env_vars)} Twitter-related environment variables")
    
    # Log credential availability (securely)
    logger.info(f"Twitter API credentials check:")
    logger.info(f"  X_API_KEY: {'✅ Present' if X_API_KEY else '❌ Missing'}")
    logger.info(f"  X_API_SECRET: {'✅ Present' if X_API_SECRET else '❌ Missing'}")
    logger.info(f"  X_ACCESS_TOKEN: {'✅ Present' if X_ACCESS_TOKEN else '❌ Missing'}")
    logger.info(f"  X_ACCESS_SECRET: {'✅ Present' if X_ACCESS_SECRET else '❌ Missing'}")
    logger.info(f"  X_BEARER_TOKEN: {'✅ Present' if X_BEARER_TOKEN else '❌ Missing'}")
    
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
        logger.error("Missing Twitter API credentials. Skipping.")
        return False
    
    try:
        # Log partial keys (safely) to verify correct credentials are being used
        logger.info(f"Using API key ending in: ...{X_API_KEY[-4:] if len(X_API_KEY) > 4 else 'too short'}")
        logger.info(f"Using access token ending in: ...{X_ACCESS_TOKEN[-4:] if len(X_ACCESS_TOKEN) > 4 else 'too short'}")
        
        # Check for non-ASCII characters that might cause issues
        import unicodedata
        for var_name, var_value in {
            'X_API_KEY': X_API_KEY,
            'X_API_SECRET': X_API_SECRET,
            'X_ACCESS_TOKEN': X_ACCESS_TOKEN,
            'X_ACCESS_SECRET': X_ACCESS_SECRET
        }.items():
            if var_value:
                # Check for invisible characters
                has_invisible = any(c.isspace() and c != ' ' for c in var_value)
                has_non_ascii = any(ord(c) > 127 for c in var_value)
                if has_invisible or has_non_ascii:
                    logger.warning(f"{var_name} contains invisible or non-ASCII characters")
                    logger.warning(f"Character breakdown: {[(c, ord(c)) for c in var_value]}")
        
        # First verify credentials to check if they're valid
        logger.info("Verifying Twitter credentials...")
        
        # Authenticate with Twitter using v2 Client
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )
        
        try:
            # Try to get the authenticated user to verify credentials
            logger.info("Attempting to verify credentials with get_me()...")
            me = client.get_me()
            if me and hasattr(me, 'data') and me.data:
                username = me.data.username
                logger.info(f"✅ Successfully authenticated as @{username}")
            else:
                logger.warning("⚠️ Authentication response format unexpected")
                logger.warning(f"Response type: {type(me)}")
                logger.warning(f"Response: {me}")
        except Exception as auth_e:
            logger.error(f"❌ Authentication verification failed: {auth_e}")
            logger.error(f"Error type: {type(auth_e).__name__}")
            
            # Try a different method to verify - just to debug
            try:
                logger.info("Attempting to verify user context with user_lookup()...")
                # Try with user_lookup as an alternative
                response = client.get_user(id="me")
                logger.info(f"User lookup response: {response}")
            except Exception as lookup_e:
                logger.error(f"User lookup also failed: {lookup_e}")
            
            # Continue anyway to try posting
        
        # Ensure tweet is within Twitter's character limit (280)
        TWITTER_CHAR_LIMIT = 280
        if len(tweet_text) > TWITTER_CHAR_LIMIT:
            logger.warning(f"Tweet exceeds Twitter's 280 character limit ({len(tweet_text)} chars). Truncating.")
            
            # Find URLs in the tweet text
            import re
            url_pattern = r'https?://\S+'
            urls = re.findall(url_pattern, tweet_text)
            
            # If we have URLs, preserve the first one
            if urls and len(urls[0]) < TWITTER_CHAR_LIMIT - 5:
                # Find the last space before the limit to avoid cutting words
                cutoff_point = tweet_text[:TWITTER_CHAR_LIMIT - 4].rfind(' ')
                if cutoff_point == -1:  # No space found
                    cutoff_point = TWITTER_CHAR_LIMIT - 4
                
                # Preserve the URL if it's after the cutoff point
                url_pos = tweet_text.find(urls[0])
                if url_pos > cutoff_point:
                    # Truncate, add ellipsis, then add the URL
                    tweet_text = tweet_text[:cutoff_point] + "... " + urls[0]
                else:
                    # URL is already in the truncated part
                    tweet_text = tweet_text[:cutoff_point] + "..."
            else:
                # No URLs or URL too long, just truncate
                cutoff_point = tweet_text[:TWITTER_CHAR_LIMIT - 4].rfind(' ')
                if cutoff_point == -1:
                    cutoff_point = TWITTER_CHAR_LIMIT - 4
                tweet_text = tweet_text[:cutoff_point] + "..."
            
            logger.info(f"Truncated tweet for Twitter: {tweet_text}")
        
        # Post the tweet using v2 API with error tracing
        logger.info(f"Attempting to post tweet to Twitter: '{tweet_text[:30]}...'")
        try:
            response = client.create_tweet(text=tweet_text)
            
            # Verify response contains expected data
            if response and hasattr(response, 'data') and response.data:
                tweet_id = response.data.get('id')
                if tweet_id:
                    logger.info(f"✅ Successfully posted to Twitter. Tweet ID: {tweet_id}")
                    return True
                else:
                    logger.warning("⚠️ Response missing tweet ID")
                    logger.warning(f"Response data: {response.data}")
                    return False
        except Exception as tweet_e:
            logger.error(f"Failed to post tweet: {tweet_e}")
            logger.error(f"Error type: {type(tweet_e).__name__}")
            # Log full exception traceback
            import traceback
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            # If this is a Forbidden error, it might be due to duplicate content
            if isinstance(tweet_e, tweepy.errors.Forbidden) and "duplicate" in str(tweet_e).lower():
                logger.error("This appears to be a duplicate tweet error. Twitter doesn't allow identical tweets.")
                # Add a timestamp to make the tweet unique
                modified_tweet = f"{tweet_text} [{datetime.now().strftime('%H:%M:%S')}]"
                logger.info(f"Trying again with timestamped tweet: {modified_tweet[:30]}...")
                try:
                    response = client.create_tweet(text=modified_tweet)
                    tweet_id = response.data.get('id') if hasattr(response, 'data') else None
                    if tweet_id:
                        logger.info(f"✅ Successfully posted modified tweet to Twitter. Tweet ID: {tweet_id}")
                        return True
                except Exception as retry_e:
                    logger.error(f"Failed to post modified tweet: {retry_e}")
            return False
    except tweepy.errors.Unauthorized as e:
        logger.error(f"❌ Twitter authentication error: {e}")
        logger.error("This usually means invalid credentials or expired tokens")
        # Check Tweepy version which might affect authentication
        logger.error(f"Tweepy version: {tweepy.__version__}")
        return False
    except tweepy.errors.Forbidden as e:
        logger.error(f"❌ Twitter permission error: {e}")
        logger.error("This usually means your app doesn't have write permissions")
        return False
    except tweepy.errors.TooManyRequests as e:
        logger.error(f"❌ Twitter rate limit exceeded: {e}")
        return False
    except tweepy.errors.BadRequest as e:
        logger.error(f"❌ Twitter bad request error: {e}")
        logger.error("This could be due to invalid tweet text or other request issues")
        return False
    except tweepy.errors.NotFound as e:
        logger.error(f"❌ Twitter resource not found: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error posting to Twitter: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def post_to_bluesky(tweet_text):
    """
    Posts a tweet to Bluesky with proper link detection for clickable URLs.
    Returns True if successful, False otherwise.
    
    The tweet text will have its URLs shortened automatically if URL shortening is enabled.
    """
    # Shorten URLs in the tweet text to save characters
    tweet_text = shorten_urls_in_text(tweet_text)
    if not all([BLUESKY_USERNAME, BLUESKY_PASSWORD]):
        logger.error("Missing Bluesky credentials. Skipping.")
        return False
    
    try:
        # Authenticate with Bluesky using the newer API style
        client = AtprotoClient()
        client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
        
        # Find URLs in the tweet text
        url_pattern = r'https?://\S+'
        urls = re.findall(url_pattern, tweet_text)
        
        # Enforce Bluesky character limit (300 graphemes)
        # We'll use a much lower limit to be safe (250 characters)
        # This is because the character count in Python is different from grapheme count in Bluesky
        BLUESKY_CHAR_LIMIT = 250
        if len(tweet_text) > BLUESKY_CHAR_LIMIT:
            logger.warning(f"Tweet exceeds Bluesky's 300 character limit ({len(tweet_text)} chars). Truncating.")
            
            # Split the tweet into two parts if possible - main content and URL
            main_content = tweet_text
            url_part = ""
            
            # If we have URLs, extract the first one to preserve it
            if urls:
                # Find the main URL we want to preserve
                main_url = urls[0]
                
                # Remove the URL from the content to measure length properly
                url_part = main_url
                main_content = tweet_text.replace(main_url, "")
                
                # Calculate how much space we have for the main content
                # Allow for ellipsis and a space between content and URL
                available_chars = BLUESKY_CHAR_LIMIT - len(url_part) - 4  # 4 chars for "... "
                
                # Truncate the main content
                if available_chars > 20:  # Make sure we have enough space for meaningful content
                    # Find the last space before the limit
                    cutoff_point = main_content[:available_chars].rfind(' ')
                    if cutoff_point == -1:  # No space found
                        cutoff_point = available_chars
                    
                    # Create the truncated tweet
                    truncated_text = main_content[:cutoff_point] + "... " + url_part
                else:
                    # Not enough space for both content and URL, prioritize URL
                    # This is an edge case - URLs are usually short enough
                    truncated_text = main_content[:BLUESKY_CHAR_LIMIT - 4] + "..."
            else:
                # No URLs, just truncate the main content
                cutoff_point = main_content[:BLUESKY_CHAR_LIMIT - 4].rfind(' ')
                if cutoff_point == -1:
                    cutoff_point = BLUESKY_CHAR_LIMIT - 4
                truncated_text = main_content[:cutoff_point] + "..."
            
            tweet_text = truncated_text
            logger.info(f"Truncated tweet for Bluesky: {tweet_text}")
            
            # Refresh URLs after truncation
            urls = re.findall(url_pattern, tweet_text)
        
        # Current time in RFC-3339 format
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        # Base record for the post
        record = {
            'text': tweet_text,
            'createdAt': current_time,
            '$type': 'app.bsky.feed.post'
        }
        
        # If URLs are found, create facets for proper link formatting
        if urls:
            facets = []
            # Convert text to bytes for proper byte indexing
            tweet_bytes = tweet_text.encode('utf-8')
            
            for url in urls:
                # Find the character position of the URL in the text
                char_start = tweet_text.find(url)
                
                if char_start >= 0:
                    char_end = char_start + len(url)
                    
                    # Convert to byte positions (important for Bluesky)
                    byte_start = len(tweet_text[:char_start].encode('utf-8'))
                    byte_end = len(tweet_text[:char_end].encode('utf-8'))
                    
                    # Create a facet for this URL
                    facet = {
                        'index': {
                            'byteStart': byte_start,
                            'byteEnd': byte_end
                        },
                        'features': [
                            {
                                '$type': 'app.bsky.richtext.facet#link',
                                'uri': url
                            }
                        ]
                    }
                    facets.append(facet)
                    logger.info(f"Created facet for URL: {url} at byte positions {byte_start}-{byte_end}")
            
            # Add the facets to the record if we have any
            if facets:
                record['facets'] = facets
                logger.info(f"Added {len(facets)} URL facets to Bluesky post")
        
        # Log the final record structure for debugging
        import json
        logger.info(f"Posting to Bluesky with record: {json.dumps(record, indent=2)}")
        
        # Create the post with properly formatted links
        response = client.app.bsky.feed.post.create(
            repo=client.me.did,
            record=record
        )
        post_uri = str(response.cid)
        post_url = f"https://bsky.app/profile/{BLUESKY_USERNAME}/post/{response.uri.split('/')[-1]}"
        
        logger.info(f"Successfully posted to Bluesky. Post URI: {post_uri}")
        logger.info(f"Bluesky post URL: {post_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error posting to Bluesky: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def get_used_tweet_indices(platform):
    """
    Retrieves previously used tweet indices for today.
    Also, handle a special case where we want to reset if we have too many used indices.
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    history_file = os.path.join(TWEETS_DIR, f"{platform}_posted_{timestamp}.json")
    
    used_indices = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                used_indices = json.load(f)
                
            # If we have used more than 50 tweets today, it's likely an error - reset the counter
            # This prevents the system from getting stuck in a state where it thinks all tweets are used
            if len(used_indices) > 50:
                logger.warning(f"Found {len(used_indices)} used indices, which seems excessive. Resetting to empty.")
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return []
                
        except Exception as e:
            logger.error(f"Error loading used tweet indices: {e}")
    
    return used_indices

def shorten_url(long_url):
    """
    Shortens a URL using a free URL shortening service.
    
    Args:
        long_url (str): The original long URL to shorten
        
    Returns:
        str: The shortened URL, or the original URL if shortening fails
    """
    # TEMPORARY: Disable URL shortening completely until issues are resolved
    logger.info(f"URL shortening disabled for now - using original URL: {long_url}")
    return long_url
    
    # Code below is temporarily disabled until URL shortening issues are resolved
    if not USE_URL_SHORTENER:
        return long_url
        
    try:
        # URL encode the long URL to handle special characters
        from urllib.parse import quote
        encoded_url = quote(long_url, safe='')
        
        # Try using TinyURL's simple API
        tinyurl_api = f"https://tinyurl.com/api-create.php?url={encoded_url}"
        response = requests.get(tinyurl_api, timeout=10)
        
        if response.status_code == 200 and response.text and response.text.startswith('https://'):
            short_url = response.text.strip()
            logger.info(f"Shortened URL: {long_url} → {short_url}")
            
            # Verify the shortened URL by testing the redirect
            try:
                verify_response = requests.head(short_url, timeout=5, allow_redirects=False)
                if verify_response.status_code in (301, 302) and 'location' in verify_response.headers:
                    redirect_url = verify_response.headers['location']
                    logger.info(f"Verified redirect: {short_url} → {redirect_url}")
                    return short_url
                else:
                    logger.warning(f"Shortened URL failed verification check: {short_url}")
                    return long_url
            except Exception as verify_e:
                logger.warning(f"Failed to verify shortened URL: {verify_e}")
                return long_url
            
        # Fallback to original URL if TinyURL fails
        logger.warning(f"Failed to shorten URL with TinyURL: {long_url}")
        return long_url
        
    except Exception as e:
        logger.error(f"Error shortening URL {long_url}: {e}")
        return long_url

def shorten_urls_in_text(text):
    """
    Finds URLs in text and replaces them with shortened versions.
    
    Args:
        text (str): The original text containing URLs
        
    Returns:
        str: Text with shortened URLs
    """
    if not USE_URL_SHORTENER:
        return text
        
    try:
        # Find URLs in the text
        url_pattern = r'https?://\S+'
        urls = re.findall(url_pattern, text)
        
        if not urls:
            return text
            
        # Make a copy of the original text
        modified_text = text
        
        # Replace each URL with its shortened version
        for url in urls:
            short_url = shorten_url(url)
            if short_url != url:
                modified_text = modified_text.replace(url, short_url)
        
        return modified_text
    except Exception as e:
        logger.error(f"Error processing URLs in text: {e}")
        return text

def is_elon_musk_tweet(tweet_text):
    """
    Checks if a tweet contains references to Elon Musk.
    Returns True if tweet mentions Elon Musk, False otherwise.
    """
    # Convert to lowercase for case-insensitive matching
    tweet_lower = tweet_text.lower()
    
    # Check for various ways to mention Elon Musk
    elon_keywords = ['elon', 'musk', 'elon musk']
    
    for keyword in elon_keywords:
        if keyword in tweet_lower:
            logger.info(f"Tweet contains Elon Musk reference: '{keyword}'")
            return True
    
    return False

def main(platform=None, count=1, similarity_threshold=0.7, force=False):
    """
    Main function to post tweets.
    
    Args:
        platform: The platform to post to (x, bluesky, or None for both)
        count: Number of tweets to post
        similarity_threshold: Threshold for similarity detection (0.0-1.0)
                              Higher values allow more similar tweets to be posted
        force: If True, bypass similarity checks completely (emergency override)
    """
    # Initialize metrics tracking
    metrics_tracker = None
    if METRICS_ENABLED:
        try:
            metrics_tracker = get_metrics_tracker()
            logger.info("Metrics tracking enabled for tweet posting")
        except Exception as e:
            logger.warning(f"Failed to initialize metrics tracking: {e}")
            logger.warning("Continuing without metrics tracking")
    # Print environment info for debugging
    import sys
    import tweepy
    
    logger.info("======== ENVIRONMENT DIAGNOSTICS ========")
    logger.info(f"🔍 Python version: {sys.version}")
    logger.info(f"🔍 Tweepy version: {tweepy.__version__}")
    logger.info(f"🔍 Current working directory: {os.getcwd()}")
    logger.info(f"🔍 Script directory: {os.path.dirname(os.path.abspath(__file__))}")
    logger.info(f"🔍 Platform(s) to post to: {platform if platform else 'both x and bluesky'}")
    logger.info(f"🔍 Number of tweets to post: {count}")
    
    # Check .env files for proper loading
    from pathlib import Path
    env_paths = [
        Path(__file__).resolve().parent.parent / '.env',
        Path(__file__).resolve().parent / '.env'
    ]
    
    for path in env_paths:
        if path.exists():
            logger.info(f"✅ Found .env file at: {path}")
            with open(path, 'r') as f:
                lines = f.readlines()
                logger.info(f"  - File has {len(lines)} lines")
                logger.info(f"  - First few keys: {', '.join([line.split('=')[0] for line in lines[:3] if '=' in line])}")
        else:
            logger.warning(f"❌ No .env file found at: {path}")
    
    platforms = ["x", "bluesky"] if platform is None else [platform]
    posted_indices = []
    platform_results = {}
    
    # Create archives directory if it doesn't exist
    os.makedirs(os.path.join(TWEETS_DIR), exist_ok=True)
    
    # Check for required archive files and create them if needed
    for p in platforms:
        archive_file = os.path.join(TWEETS_DIR, f"{p}_posted_tweets_archive.txt")
        if not os.path.exists(archive_file):
            # Create empty archive file
            logger.info(f"Creating empty archive file for {p} at {archive_file}")
            try:
                with open(archive_file, 'w', encoding='utf-8') as f:
                    f.write("# Archive of all posted tweets for similarity detection\n")
                    f.write("# Format: [timestamp] tweet text\n")
                    f.write("# Separator: ---\n\n")
            except Exception as e:
                logger.error(f"Failed to create archive file {archive_file}: {e}")
    
    # Process each platform
    for p in platforms:
        logger.info(f"\n==== Processing platform: {p} ====")
        
        # Load tweets for the platform
        tweets = load_tweets(p)
        if not tweets:
            logger.warning(f"No tweets available for {p}. Skipping.")
            platform_results[p] = {"status": "skipped", "reason": "no_tweets_available"}
            continue
            
        # Get already used tweet indices
        used_indices = get_used_tweet_indices(p)
        logger.info(f"Found {len(used_indices)} already used tweet indices for today")
        
        # Log the current similarity threshold being used
        logger.info(f"Using similarity threshold: {similarity_threshold} (higher = more similar tweets allowed)")
        
        # Load ALL previously posted tweets for thorough similarity checking
        # This is crucial for preventing duplicates
        recent_tweets = load_recently_posted_tweets(p, days=30)  # Increased from 7 to 30 days
        logger.info(f"Loaded {len(recent_tweets)} tweets for similarity checking")
        
        # Check if we need to reset the used indices - if most tweets are marked as used
        if len(used_indices) > 0 and len(used_indices) >= len(tweets) * 0.8:
            logger.warning(f"Too many used indices ({len(used_indices)}) compared to available tweets ({len(tweets)}). Resetting used indices.")
            used_indices = []
            # Reset the history file
            timestamp = datetime.now().strftime("%Y%m%d")
            history_file = os.path.join(TWEETS_DIR, f"{p}_posted_{timestamp}.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        # Get available indices (not used today)
        available_indices = [i for i in range(len(tweets)) if i not in used_indices]
        logger.info(f"Found {len(available_indices)} available tweets to post")
        
        if not available_indices:
            logger.warning(f"All tweets already used today for {p}. Skipping.")
            platform_results[p] = {"status": "skipped", "reason": "all_tweets_used"}
            continue
        
        # Double-check: make sure tweets in the available indices aren't duplicates
        # by performing content-based checks directly against our recent tweet pool
        double_checked_indices = []
        duplicate_count = 0
        
        logger.info(f"Performing content-based duplicate check on {len(available_indices)} available tweets...")
        
        for idx in available_indices:
            tweet = tweets[idx]
            
            # First apply any platform-specific filtering
            if p == "x" and is_elon_musk_tweet(tweet):
                logger.info(f"Tweet #{idx} mentions Elon Musk, skipping for X platform")
                continue
            
            # Check if this tweet is a duplicate based on content
            # This is our bulletproof check to prevent duplicate posts
            is_duplicate = False
            
            # Skip duplicate check if force mode is enabled
            if force:
                logger.info(f"FORCE mode enabled - bypassing duplicate checks for tweet #{idx}")
                double_checked_indices.append(idx)
                continue
            
            # Check duplicate by content
            if is_similar_to_existing(tweet, recent_tweets, similarity_threshold):
                logger.warning(f"Tweet #{idx} content matches an existing tweet. Marking as duplicate.")
                duplicate_count += 1
                is_duplicate = True
            
            if not is_duplicate:
                double_checked_indices.append(idx)
        
        logger.info(f"Content duplicate check found {duplicate_count} duplicates, {len(double_checked_indices)} tweets passed")
        
        # Now use the double-checked indices instead of the original available indices
        available_indices = double_checked_indices
        
        if not available_indices:
            logger.warning(f"All available tweets are duplicates for {p}. Skipping.")
            platform_results[p] = {"status": "skipped", "reason": "all_tweets_are_duplicates"}
            continue
        
        # Calculate uniqueness scores for each available tweet
        logger.info("Ranking tweets by uniqueness score...")
        tweet_uniqueness_scores = []
        
        for idx in available_indices:
            tweet = tweets[idx]
            # Calculate uniqueness by comparing this tweet to all other available tweets
            total_similarity = 0
            comparisons = 0
            
            for other_idx in available_indices:
                if idx == other_idx:
                    continue
                    
                other_tweet = tweets[other_idx]
                # Use difflib to measure similarity
                import difflib
                
                # Normalize for comparison
                def normalize_text(text):
                    text = re.sub(r'https?://\S+', '', text)
                    text = re.sub(r'#\w+', '', text)
                    return text.lower().strip()
                
                normalized_tweet = normalize_text(tweet)
                normalized_other = normalize_text(other_tweet)
                
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, normalized_tweet, normalized_other).ratio()
                total_similarity += similarity
                comparisons += 1
            
            # Calculate average similarity, then convert to uniqueness score
            avg_similarity = total_similarity / max(comparisons, 1)
            uniqueness_score = 1 - avg_similarity
            
            tweet_uniqueness_scores.append((idx, uniqueness_score, tweet))
            logger.info(f"Tweet #{idx} uniqueness score: {uniqueness_score:.2f}")
        
        # Sort by uniqueness score (highest first)
        tweet_uniqueness_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Choose the most unique tweets up to the requested count
        num_to_post = min(count, len(tweet_uniqueness_scores))
        indices_to_post = [idx for idx, _, _ in tweet_uniqueness_scores[:num_to_post]]
        
        # Log the selected tweets with their uniqueness scores
        logger.info("Selected tweets by uniqueness ranking:")
        for i, (idx, score, tweet_text) in enumerate(tweet_uniqueness_scores[:num_to_post]):
            logger.info(f"  {i+1}. Tweet #{idx} (score: {score:.2f}): {tweet_text[:50]}...")
        logger.info(f"Selected {len(indices_to_post)} tweets to post")
        
        # Final sanity check: one last check for duplicates before posting
        # This is paranoid but necessary to prevent duplicate posts
        skipped_indices = []
        final_indices_to_post = []
        
        logger.info("Performing final duplicate check before posting...")
        for idx in indices_to_post:
            tweet = tweets[idx]
            
            # One last check against recent tweets to be safe
            if not force and is_similar_to_existing(tweet, recent_tweets, similarity_threshold):
                logger.warning(f"Final check: Tweet #{idx} still seems to be a duplicate. Skipping.")
                skipped_indices.append(idx)
                continue
                
            final_indices_to_post.append(idx)
        
        if skipped_indices:
            logger.warning(f"Final check skipped {len(skipped_indices)} tweets that appear to be duplicates")
        
        if not final_indices_to_post:
            logger.warning(f"After final checks, no tweets remain to post for {p}. Skipping.")
            platform_results[p] = {"status": "skipped", "reason": "all_tweets_filtered_out"}
            continue
            
        # Post each tweet
        platform_posted = []
        posted_tweet_texts = []
        for idx in final_indices_to_post:
            tweet = tweets[idx]
            logger.info(f"Posting tweet #{idx}: {tweet[:50]}...")
            
            # Post based on platform
            success = False
            if p == "x":
                success = post_to_twitter(tweet)
            elif p == "bluesky":
                success = post_to_bluesky(tweet)
            
            if success:
                platform_posted.append(idx)
                posted_indices.append(idx)
                posted_tweet_texts.append(tweet)
                logger.info(f"Successfully posted tweet #{idx}")
                
                # Add tweet to in-memory list of recent tweets to prevent posting duplicates in same batch
                recent_tweets.append(tweet)
                
                # Add a delay between posts to avoid rate limits
                if idx != final_indices_to_post[-1]:
                    logger.info(f"Waiting 5 seconds before next post...")
                    time.sleep(5)
            else:
                logger.error(f"Failed to post tweet #{idx}")
        
        # Save posted indices and ONLY the tweets that were actually posted
        if platform_posted:
            logger.info(f"Saving {len(platform_posted)} used tweet IDs for {p}")
            logger.info(f"Archiving {len(posted_tweet_texts)} successfully posted tweets")
            save_used_tweet_ids(p, used_indices + platform_posted, posted_tweet_texts)  # Only archive successfully posted tweets
            platform_results[p] = {"status": "success", "count": len(platform_posted)}
        else:
            logger.warning(f"No tweets were successfully posted to {p}")
            platform_results[p] = {"status": "failed", "count": 0}
    
    # Log summary of results
    logger.info("\n==== POSTING SUMMARY ====")
    for p, result in platform_results.items():
        status = result["status"]
        if status == "success":
            logger.info(f"{p}: ✅ Posted {result['count']} tweets successfully")
        elif status == "failed":
            logger.info(f"{p}: ❌ Failed to post any tweets")
        else:
            logger.info(f"{p}: ⚠️ Skipped ({result['reason']})")
            
    logger.info(f"Posted {len(posted_indices)} tweets successfully.")
    
    # Record posting metrics
    if metrics_tracker:
        try:
            for p, result in platform_results.items():
                if result["status"] == "success":
                    attempted = len(final_indices_to_post) if "final_indices_to_post" in locals() else 0
                    posted = result["count"]
                    metrics_tracker.log_posting_results(
                        platform=p,
                        attempted=attempted,
                        posted=posted,
                        similarity_threshold=similarity_threshold
                    )
                    logger.info(f"Recorded posting metrics for {p}: {posted}/{attempted} tweets")
            # Generate daily report
            report = metrics_tracker.generate_daily_report()
            logger.info(f"Daily metrics report generated and saved")
        except Exception as e:
            logger.warning(f"Failed to record posting metrics: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), '../logs'), exist_ok=True)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Post tweets to social media platforms")
    parser.add_argument("--platform", choices=["x", "bluesky"], help="Platform to post to (default: both)")
    parser.add_argument("--count", type=int, default=1, help="Number of tweets to post (default: 1)")
    parser.add_argument("--similarity-threshold", type=float, default=0.9, 
                       help="Similarity threshold for filtering tweets (0.0-1.0, higher means more similar tweets will be posted)")
    parser.add_argument("--force", action="store_true", 
                       help="Force posting by bypassing similarity checks (emergency override)")
    parser.add_argument("--no-url-shortening", action="store_true",
                       help="Disable URL shortening for posts")
    parser.add_argument("--x-wait-time", type=int, default=60,
                       help="Time to wait between X posts in seconds (default: 60)")
    parser.add_argument("--bluesky-wait-time", type=int, default=5,
                       help="Time to wait between Bluesky posts in seconds (default: 5)")
    parser.add_argument("--separate", action="store_true",
                       help="Use separate platform-specific posting processes (recommended to avoid rate limits)")
    args = parser.parse_args()
    
    # Check if we should use the new separate platform scripts
    if args.separate:
        import subprocess
        import sys
        
        logger.info("Using separate platform-specific posting processes")
        
        # Determine which platforms to post to
        platforms = ["x", "bluesky"] if args.platform is None else [args.platform]
        
        # Build common arguments for both scripts
        common_args = [
            "--count", str(args.count),
            "--similarity-threshold", str(args.similarity_threshold)
        ]
        
        if args.force:
            common_args.append("--force")
            
        if args.no_url_shortening:
            common_args.append("--no-url-shortening")
        
        # Run platform-specific scripts
        results = {}
        
        for platform in platforms:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"post_to_{platform}.py")
            
            # Add platform-specific arguments
            platform_args = common_args.copy()
            if platform == "x":
                platform_args.extend(["--wait-time", str(args.x_wait_time)])
            elif platform == "bluesky":
                platform_args.extend(["--wait-time", str(args.bluesky_wait_time)])
            
            # Check if script exists
            if not os.path.exists(script_path):
                logger.error(f"Platform script {script_path} not found. Skipping {platform}.")
                results[platform] = {"status": "error", "reason": "script_not_found"}
                continue
            
            # Make script executable
            try:
                import stat
                st = os.stat(script_path)
                os.chmod(script_path, st.st_mode | stat.S_IEXEC)
            except Exception as e:
                logger.warning(f"Could not make script executable: {e}")
            
            # Run the script
            logger.info(f"Starting {platform} posting process with args: {platform_args}")
            cmd = [sys.executable, script_path] + platform_args
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"{platform}: Process completed successfully")
                    results[platform] = {"status": "success"}
                else:
                    logger.error(f"{platform}: Process failed with code {result.returncode}")
                    logger.error(f"Error output: {result.stderr}")
                    results[platform] = {"status": "error", "reason": "process_failed"}
            except Exception as e:
                logger.error(f"Error running {platform} script: {e}")
                results[platform] = {"status": "error", "reason": "exception"}
        
        # Log summary
        logger.info("\n==== POSTING SUMMARY ====")
        for p, result in results.items():
            status = result["status"]
            if status == "success":
                logger.info(f"{p}: ✅ Process completed successfully")
            else:
                reason = result.get("reason", "unknown")
                logger.info(f"{p}: ❌ Process failed ({reason})")
                
        logger.info("All posting processes completed")
    else:
        # Apply command-line settings for the combined process
        if args.no_url_shortening:
            USE_URL_SHORTENER = False
            logger.info("URL shortening disabled by command-line argument")
        
        # Call main function with the original combined approach
        logger.info("Using combined posting process (may encounter rate limits)")
        main(args.platform, args.count, args.similarity_threshold, args.force)