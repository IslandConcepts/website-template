#!/usr/bin/env python
# This script generates various types of tweets for social media accounts
# It will generate tweets based on different approaches:
# 1. Article summaries with links
# 2. News references
# 3. Commentary on current events
# 4. Content based on site keywords
#
# The script now generates a pool of tweets (default: 25) and selects
# the most unique ones based on content similarity analysis to ensure we always
# have fresh, unique content for social media posting.
#
# Usage example: python generate_tweets.py --count 3 --pool-size 25 --platform both

import os
import sys
import random
import json
import time
import re
from datetime import datetime
import html
from collections import defaultdict
import logging
import argparse
from openai import OpenAI

# Import tweet metrics tracker
try:
    from tweet_metrics import get_metrics_tracker
    METRICS_ENABLED = True
except ImportError:
    print("Tweet metrics module not found, metrics tracking disabled")
    METRICS_ENABLED = False

# Setup logging with more verbose output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create a file handler to log to a file as well
try:
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"tweet_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Logging to file: {log_file}")
except Exception as e:
    logger.warning(f"Could not set up file logging: {e}")

# Try to get API key from environment first, then fall back to hardcoded key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable not set, falling back to hardcoded key.")
    OPENAI_API_KEY = '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'

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Get base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
TWEETS_DIR = os.path.join(BASE_DIR, "tweets")

# Default temperature settings for different generation functions
# Using a dictionary for temperature settings to avoid global variable issues
TEMP_SETTINGS = {
    "hashtag": 0.5,    # For hashtag generation (always this value)
    "commentary": 0.8,  # For general commentary tweets
    "article": 0.85,   # For article summary tweets (increased for more creative commentary)
    "absurd": 0.7,     # For absurd take tweets
    "leak": 0.85       # For Signal leak tweets (increased for more creative takes)
}

# Define a function to get temperature values
def get_temp(temp_type):
    return TEMP_SETTINGS.get(temp_type, 0.7)  # Return 0.7 as default if key not found

# Ensure tweets directory exists
os.makedirs(TWEETS_DIR, exist_ok=True)

def load_existing_tweets():
    """
    Load tweets that have already been posted to avoid duplicates
    """
    existing_tweets = []
    
    try:
        for filename in os.listdir(TWEETS_DIR):
            if (filename.endswith("_tweets.txt") or filename.endswith("tweets.txt")) and not filename.startswith("."):
                with open(os.path.join(TWEETS_DIR, filename), 'r', encoding='utf-8') as f:
                    existing_tweets.extend([line.strip() for line in f.readlines() if line.strip()])
    except Exception as e:
        logger.warning(f"Error reading existing tweets: {e}")
    
    logger.info(f"Loaded {len(existing_tweets)} existing tweets")
    return existing_tweets

def save_tweets(platform, tweets):
    """
    Save generated tweets to a daily text file - reuse the same file all day
    """
    # Use date without timestamp for consistent daily file
    date_only = datetime.now().strftime("%Y%m%d")
    filename = f"tweets_{date_only}.txt"  # Use common filename for shared tweets
    filepath = os.path.join(TWEETS_DIR, filename)
    
    # Check if the file already exists
    existing_tweets = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if '---' in content:
                existing_tweets = [tweet.strip() for tweet in content.split('---') if tweet.strip()]
            else:
                existing_tweets = [line.strip() for line in content.splitlines() if line.strip()]
        
        logger.info(f"Found existing tweet file with {len(existing_tweets)} tweets")
    
    # Append new tweets that aren't already in the file
    new_tweets = []
    for tweet in tweets:
        if tweet not in existing_tweets:
            new_tweets.append(tweet)
    
    # Write to file - if exists, append; if new, write
    if new_tweets:
        separator = "---\n"
        
        if existing_tweets:
            # File exists, append new tweets
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(separator + separator.join(new_tweets) + separator)
        else:
            # New file, write tweets with separators
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(separator.join(new_tweets) + separator)
        
        logger.info(f"Added {len(new_tweets)} new tweets to {filepath}")
    else:
        logger.info(f"No new tweets to add to {filepath}")
    
    # Also create platform-specific symbolic links for backward compatibility
    platform_filename = f"{platform}_tweets_{date_only}.txt"
    platform_filepath = os.path.join(TWEETS_DIR, platform_filename)
    
    try:
        # Create a hard copy of the file for backward compatibility
        import shutil
        shutil.copy2(filepath, platform_filepath)
        logger.info(f"Created platform-specific copy at {platform_filepath}")
    except Exception as e:
        logger.error(f"Error creating platform-specific copy: {e}")
    
    return filepath

def load_articles(days_back=2):
    """
    Load available articles from the content directory from the last N days
    
    Args:
        days_back: Number of days to look back for recent content (default: 2)
    """
    articles = []
    recent_articles = []
    total_articles_seen = 0
    
    # Get the date from N days ago for filtering
    from datetime import datetime, timedelta
    today = datetime.now()
    cutoff_date = today - timedelta(days=days_back)
    cutoff_date_str = cutoff_date.strftime("%Y%m%d")
    logger.info(f"Using cutoff date for recent articles: {cutoff_date_str} (looking back {days_back} days)")
    
    # Extract date from filename function
    def get_file_date(filename):
        # Try to extract date in format YYYYMMDD from the end of the filename
        # Example: Some_Title_20250425073045.md
        import re
        date_match = re.search(r'_(\d{8})\d+\.md$', filename)
        if date_match:
            return date_match.group(1)  # Return just YYYYMMDD part
        return None
    
    # Check news section
    news_dir = os.path.join(CONTENT_DIR, "news")
    news_count = 0
    if os.path.exists(news_dir):
        for filename in os.listdir(news_dir):
            if filename.endswith(".md") and not filename.startswith("_"):
                total_articles_seen += 1
                filepath = os.path.join(news_dir, filename)
                
                # Get the date from the filename
                file_date = get_file_date(filename)
                
                # Debug the date extraction
                logger.debug(f"News file: {filename}, extracted date: {file_date}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    article = {
                        "title": filename.replace(".md", "").replace("_", " "),
                        "path": f"/news/{filename.replace('.md', '')}",
                        "content": content,
                        "type": "news",
                        "date": file_date
                    }
                    
                    articles.append(article)
                    
                    # Add to recent articles if within the last 2 days
                    if file_date and file_date >= cutoff_date_str:
                        recent_articles.append(article)
                        news_count += 1
                        logger.debug(f"Added recent news: {filename}")
    
    logger.info(f"Found {news_count} recent news articles from the last 2 days")
    
    # Check posts section
    posts_dir = os.path.join(CONTENT_DIR, "posts")
    posts_count = 0
    if os.path.exists(posts_dir):
        for filename in os.listdir(posts_dir):
            if filename.endswith(".md") and not filename.startswith("_"):
                total_articles_seen += 1
                filepath = os.path.join(posts_dir, filename)
                
                # Get the date from the filename
                file_date = get_file_date(filename)
                
                # Debug the date extraction
                logger.debug(f"Post file: {filename}, extracted date: {file_date}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    article = {
                        "title": filename.replace(".md", "").replace("_", " "),
                        "path": f"/posts/{filename.replace('.md', '')}",
                        "content": content,
                        "type": "post",
                        "date": file_date
                    }
                    
                    articles.append(article)
                    
                    # Add to recent articles if within the last 2 days
                    if file_date and file_date >= cutoff_date_str:
                        recent_articles.append(article)
                        posts_count += 1
                        logger.debug(f"Added recent post: {filename}")
    
    logger.info(f"Found {posts_count} recent posts from the last 2 days")
    
    # Skipping the trends section entirely as all content is classified documents
    logger.info("Skipping trends section as requested - all content consists of classified document leaks")
    
    # Display detailed statistics
    logger.info(f"Examined {total_articles_seen} total articles")
    logger.info(f"Found {len(recent_articles)} recent articles from last 2 days (since {cutoff_date_str})")
    logger.info(f"All articles: {len(articles)}, Using only recent: {len(recent_articles)}")
    
    # Return only recent articles
    return recent_articles

def load_news_items(days_back=2):
    """
    Load latest news items from the last N days
    
    Args:
        days_back: Number of days to look back for recent content (default: 2)
    """
    news_items = []
    checked_items = 0
    matched_items = 0
    
    # Get the date from N days ago for filtering
    from datetime import datetime, timedelta
    today = datetime.now()
    cutoff_date = today - timedelta(days=days_back)
    cutoff_date_str = cutoff_date.strftime("%Y%m%d")
    logger.info(f"Using cutoff date for recent news items: {cutoff_date_str} (looking back {days_back} days)")
    
    # Try to load from recent daily news files
    daily_news_files = []
    for filename in os.listdir(os.path.join(BASE_DIR, "scripts")):
        if filename.startswith("daily_news_") and filename.endswith(".json"):
            # Extract date from filename (format: daily_news_YYYYMMDD.json)
            file_date = filename.replace("daily_news_", "").replace(".json", "")
            
            # Only add if it's from the last 2 days
            if file_date and file_date >= cutoff_date_str:
                daily_news_files.append(os.path.join(BASE_DIR, "scripts", filename))
                logger.info(f"Including daily news file: {filename} (date: {file_date})")
            else:
                logger.debug(f"Skipping older daily news file: {filename} (date: {file_date})")
    
    # Sort by most recent
    daily_news_files.sort(reverse=True)
    
    # Look for relevant news about leaks
    for file in daily_news_files:
        logger.info(f"Processing news file: {os.path.basename(file)}")
        try:
            with open(file, 'r', encoding='utf-8') as f:
                news_items = json.load(f)
                
                # Only process items from the file if we found valid news
                if not news_items or not isinstance(news_items, list):
                    logger.warning(f"File {file} contains invalid news data (empty or not a list)")
                    continue
                    
                logger.info(f"File {os.path.basename(file)} contains {len(news_items)} news items")
                
                for item in news_items:
                    checked_items += 1
                    title = item.get("title", "").lower()
                    description = item.get("description", "").lower()
                    
                    # Try to get keywords from config if available
                    try:
                        from config_loader import ConfigLoader
                        config = ConfigLoader()
                        news_keywords = config.get_keywords_list("news_keywords")
                        if not news_keywords: # Fallback to default keywords
                            news_keywords = ["breaking", "news", "report", "update", "latest", "story", "exclusive", "announcement", "trending", "important", "development", "press release"]
                    except Exception as e:
                        logger.warning(f"Could not load news keywords from config: {e}")
                        # Fallback to default keywords
                        news_keywords = ["breaking", "news", "report", "update", "latest", "story", "exclusive", "announcement", "trending", "important", "development", "press release"]
                    
                    # Check if any keywords are in the title or description
                    matched_keywords = []
                    for keyword in news_keywords:
                        if keyword in title or keyword in description:
                            matched_keywords.append(keyword)
                    
                    if matched_keywords:
                        news_items.append(item)
                        matched_items += 1
                        logger.debug(f"Found news item: '{title}' (matched keywords: {', '.join(matched_keywords)})")
        except Exception as e:
            logger.warning(f"Error loading leaks from {file}: {e}")
    
    # Display detailed statistics
    logger.info(f"Checked {checked_items} total news items across {len(daily_news_files)} recent daily news files")
    logger.info(f"Found {matched_items} items matching news keywords")
    logger.info(f"Final count: {len(news_items)} news items from the last {days_back} days")
    
    return news_items

def generate_relevant_hashtags(tweet_text, count=2):
    """
    Generate 1-3 relevant hashtags for a tweet based on its content.
    """
    # Extract the main content without URLs for better hashtag generation
    main_content = re.sub(r'https?://\S+', '', tweet_text).strip()
    
    prompt = f"""
    Generate {count} hashtags for this tweet:
    "{main_content}"
    
    Guidelines:
    - Return ONLY hashtags, no commentary
    - Use popular, generic hashtags that people would search for
    - Examples: #Trump #Pentagon #WhiteHouse #DOGE #Tesla #UFO #Biden
    - Avoid niche or complex hashtags like #EarthdayLeaks or #TrumpLeaks
    - Use simple, single-word hashtags that are commonly searched
    - Only return {count} hashtags total
    - Format without spaces (e.g., #Pentagon not #The Pentagon)
    - Focus on popular topics, people, organizations mentioned in the tweet
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a hashtag generator for popular social media posts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=get_temp("hashtag")
        )
        
        hashtag_text = response.choices[0].message.content.strip()
        hashtags = re.findall(r'#\w+', hashtag_text)
        
        # If it didn't return hashtags in the right format, try to fix
        if not hashtags:
            potential_tags = hashtag_text.split()
            hashtags = ["#" + word.strip("#").strip() for word in potential_tags if word.strip()]
            # Filter out any non-hashtags
            hashtags = [tag for tag in hashtags if re.match(r"^#\w+$", tag)]
        
        # Limit to requested count
        hashtags = hashtags[:count]
        logger.info(f"Generated hashtags: {hashtags}")
        return hashtags
    except Exception as e:
        logger.error(f"Error generating hashtags: {e}")
        return []

def generate_commentary_tweet(retries=3, base_delay=5):
    """
    Generate a random commentary tweet about current events
    """
    # Get site name from config or use placeholder
    try:
        from config_loader import ConfigLoader
        config = ConfigLoader()
        site_name = config.get_value("site.info.title", "{{site_title}}")
        # Get tweet prompt from config or use default
        prompt_text = config.get_prompt_text("news", "tweet_prompt")
        if prompt_text:
            prompt = prompt_text
        else:
            prompt = f"""
            Generate a tweet for {site_name}.

            The tweet should:
            1. Be short (under 200 characters)
            2. Be attention-grabbing and interesting
            3. Be formatted as a standalone tweet (no hashtags or @mentions)
            4. Focus on current events or trending topics
            5. Use appropriate tone based on the site's focus
            
            Write the tweet as if from an authoritative news source.
            """
    except Exception as e:
        logger.warning(f"Could not load config for prompt: {e}")
        prompt = """
        Generate a tweet about current events.

        The tweet should:
        1. Be short (under 200 characters)
        2. Be attention-grabbing and interesting
        3. Be formatted as a standalone tweet (no hashtags or @mentions)
        4. Focus on trending topics or news
        
        Write the tweet as if from a news publisher.
        """
    
    max_attempts = retries
    for attempt in range(max_attempts):
        try:
            messages = [
                {"role": "system", "content": "You are a writer for a satirical political news site that publishes absurd but plausible-sounding leaks about the U.S. government."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,
                temperature=get_temp("commentary")
            )
            
            tweet = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            tweet = re.sub(r'^"|"$', '', tweet)
            
            # If tweet is too long, regenerate a shorter one instead of truncating
            if len(tweet) > 240 and attempt < retries - 1:
                logger.warning(f"Tweet too long ({len(tweet)} chars). Retrying...")
                time.sleep(base_delay * (attempt + 1))
                continue
            
            # Trim if needed as a last resort
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."
            
            # Generate and add hashtags if there's room
            hashtag_count = random.randint(1, 3)
            hashtags = generate_relevant_hashtags(tweet, hashtag_count)
            hashtag_text = " ".join(hashtags) if hashtags else ""
            
            # Add hashtags if there's room, always at the very end
            if hashtag_text and len(tweet) + len(hashtag_text) + 1 <= 280:
                tweet = f"{tweet} {hashtag_text}"
                
            logger.info(f"Generated commentary tweet ({len(tweet)} chars)")
            return tweet
            
        except Exception as e:
            logger.error(f"Error generating commentary tweet (attempt {attempt+1}/{max_attempts}): {str(e)}")
            if attempt < max_attempts - 1:
                sleep_time = base_delay * (attempt + 1)
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Max retries reached for generating commentary tweet")
                return None

def generate_article_summary_tweet(article, retries=3, base_delay=5):
    """
    Generate a tweet summarizing an article and including its URL
    """
    title = article["title"]
    article_type = article["type"]
    
    # Extract first paragraph of content
    content = article["content"]
    first_para = ""
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---") and len(line) > 50:
            first_para = line
            break
    
    # Get site URL from config or use placeholder
    try:
        from config_loader import ConfigLoader
        config = ConfigLoader()
        site_url = config.get_value("site.info.baseURL", "{{site_url}}")
    except Exception as e:
        logger.warning(f"Could not load site URL from config: {e}")
        site_url = os.environ.get("SITE_URL", "{{site_url}}")
    
    url = f"{site_url}{article['path']}"
    
    max_text_length = 280 - (len(url) + 1)  # Leave room for URL and space
    
    prompt = f"""
    Write a tweet promoting this {article_type} article.
    
    Title: {title}
    
    First paragraph: {first_para[:300]}...
    
    The tweet should:
    1. Be concise and attention-grabbing (under {max_text_length - 30} characters)
    2. Present it as a leaked story (don't say it's satire) but MUST feature a STRONGLY absurd, sardonic or surreal take on the story.
    3. NEVER simply summarize the article - instead, add a bizarre editorial angle or extreme exaggeration that transforms the content.
    4. Add commentary that suggests hidden motives, ridiculous consequences, or absurd behind-the-scenes details.
    5. Use dry, matter-of-fact language to describe something completely ridiculous or absurd.
    6. Make it sound like classified information that reveals an absurd truth.
    7. For third-party articles especially, add a strong satirical interpretation rather than just repeating facts.
    8. Do NOT include the URL (we'll add that separately)
    9. Do NOT include hashtags (we'll add those separately)
    
    IMPORTANT: Your tweet MUST include commentary or satire - not just facts from the article.
    EXAMPLES:
    - Instead of "Report shows inflation rising" → "Treasury memo reveals staff using Monopoly money to understand inflation since real dollars 'too complicated'"
    - Instead of "Supreme Court rules on case" → "Leaked SCOTUS group chat shows Justices decided major case with rock-paper-scissors tournament"
    
    Write ONLY the tweet text, nothing else.
    """
    
    max_attempts = retries
    for attempt in range(max_attempts):
        try:
            messages = [
                {"role": "system", "content": "You are a satirical writer for a political news site that publishes absurd interpretations of leaked government information. Your specialty is creating ironic, exaggerated, and sardonic commentary that sounds serious but is completely ridiculous."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,
                temperature=get_temp("article")
            )
            
            tweet_text = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            tweet_text = re.sub(r'^"|"$', '', tweet_text)
            
            # If tweet is too long, regenerate a shorter one instead of truncating
            if len(tweet_text) > max_text_length - 5 and attempt < retries - 1:
                logger.warning(f"Tweet text too long ({len(tweet_text)} chars). Retrying...")
                time.sleep(base_delay * (attempt + 1))
                continue
                
            # Truncate as a last resort
            if len(tweet_text) > max_text_length - 5:
                tweet_text = tweet_text[:max_text_length - 8] + "..."
            
            # First form the tweet with the main content and URL
            tweet = f"{tweet_text} {url}"
            
            # Generate 1-3 hashtags
            hashtag_count = random.randint(1, 3)
            hashtags = generate_relevant_hashtags(tweet_text, hashtag_count)
            hashtag_text = " ".join(hashtags) if hashtags else ""
            
            # Add hashtags if there's room, always at the very end
            if hashtag_text and len(tweet) + len(hashtag_text) + 1 <= 280:
                tweet = f"{tweet} {hashtag_text}"
                
            logger.info(f"Generated article tweet ({len(tweet)} chars) for {title}")
            return tweet
            
        except Exception as e:
            logger.error(f"Error generating article tweet (attempt {attempt+1}/{max_attempts}): {str(e)}")
            if attempt < max_attempts - 1:
                sleep_time = base_delay * (attempt + 1)
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Max retries reached for generating article tweet")
                return None

def generate_absurd_take_tweet(retries=3, base_delay=5):
    """
    Generate an absurd take on a current government or political topic
    """
    # Try to get prompt from config
    try:
        from config_loader import ConfigLoader
        config = ConfigLoader()
        site_name = config.get_value("site.info.title", "{{site_title}}")
        # Get tweet prompt from config or use default
        prompt_text = config.get_prompt_text("news", "absurd_tweet_prompt")
        if prompt_text:
            prompt = prompt_text
        else:
            prompt = f"""
            Generate an interesting tweet for {site_name} about a recent news story or event.

            The tweet should:
            1. Be concise (under 200 characters)
            2. Be attention-grabbing and unique
            3. Have a creative angle or perspective
            4. Use appropriate language for the topic
            5. Be formatted clearly for social media
            
            Make it sound like a breaking news or feature story.
            """
    except Exception as e:
        logger.warning(f"Could not load config for prompt: {e}")
        prompt = """
        Generate an interesting tweet about a recent news story or trending topic.

        The tweet should:
        1. Be concise (under 200 characters)
        2. Be attention-grabbing and unique
        3. Have a creative angle or perspective
        4. Be formatted clearly for social media
        
        Make it sound interesting and shareable.
        """
    
    max_text_length = 280
    
    max_attempts = retries
    for attempt in range(max_attempts):
        try:
            messages = [
                {"role": "system", "content": "You are a writer for a satirical political news site that specializes in absurd government leaks."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,
                temperature=get_temp("absurd")
            )
            
            tweet_text = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            tweet_text = re.sub(r'^"|"$', '', tweet_text)
            
            # If tweet is too long, regenerate a shorter one instead of truncating
            if len(tweet_text) > max_text_length - 5 and attempt < retries - 1:
                logger.warning(f"Tweet text too long ({len(tweet_text)} chars). Retrying...")
                time.sleep(base_delay * (attempt + 1))
                continue
                
            # Truncate as a last resort
            if len(tweet_text) > max_text_length - 5:
                tweet_text = tweet_text[:max_text_length - 8] + "..."
            
            # Generate 1-3 hashtags
            hashtag_count = random.randint(1, 3)
            hashtags = generate_relevant_hashtags(tweet_text, hashtag_count)
            hashtag_text = " ".join(hashtags) if hashtags else ""
            
            # Add hashtags if there's room, always at the very end
            if hashtag_text and len(tweet_text) + len(hashtag_text) + 1 <= 280:
                tweet = f"{tweet_text} {hashtag_text}"
            else:
                tweet = tweet_text
                
            logger.info(f"Generated absurd take tweet ({len(tweet)} chars)")
            return tweet
            
        except Exception as e:
            logger.error(f"Error generating absurd take tweet (attempt {attempt+1}/{max_attempts}): {str(e)}")
            if attempt < max_attempts - 1:
                sleep_time = base_delay * (attempt + 1)
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Max retries reached for generating absurd take tweet")
                return None

def generate_news_tweet(leak, retries=3, base_delay=5):
    """
    Generate a tweet based on a news item
    """
    title = leak.get("title", "")
    description = leak.get("description", "")
    url = leak.get("url", "")
    
    # Try to get prompt from config
    try:
        from config_loader import ConfigLoader
        config = ConfigLoader()
        # Get tweet prompt from config or use default
        prompt_text = config.get_prompt_text("news", "news_tweet_prompt")
        if prompt_text:
            # Replace variables in the template
            prompt = config.process_template(prompt_text, {"title": title, "description": description})
        else:
            prompt = f"""
            Generate a tweet about the following news:
            
            Title: {title}
            
            Description: {description}
            
            The tweet should:
            1. Be short and attention-grabbing (under 200 characters)
            2. Include a unique perspective or insight about the news
            3. Be creative but factual
            4. Use engaging language
            5. Be appropriate for the topic
            6. Do NOT include the URL (we'll add that separately)
            
            IMPORTANT: Your tweet should be interesting and shareable.
            
            Write ONLY the tweet text, nothing else.
            """
    except Exception as e:
        logger.warning(f"Could not load config for prompt: {e}")
        prompt = f"""
        Generate a tweet about the following news:
        
        Title: {title}
        
        Description: {description}
        
        The tweet should:
        1. Be short and attention-grabbing (under 200 characters)
        2. Include a unique perspective or insight
        3. Be creative but factual
        4. Do NOT include the URL (we'll add that separately)
        
        Write ONLY the tweet text, nothing else.
        """
    
    max_text_length = 280
    if url:
        max_text_length = 280 - (len(url) + 1)  # Leave room for URL and space
    
    max_attempts = retries
    for attempt in range(max_attempts):
        try:
            messages = [
                {"role": "system", "content": "You are a satirical writer for a political news site that specializes in absurd interpretations of leaked government information. You excel at creating deadpan, ridiculous 'insider' commentary that sounds official but is completely absurd."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,
                temperature=get_temp("leak")
            )
            
            tweet_text = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            tweet_text = re.sub(r'^"|"$', '', tweet_text)
            
            # If tweet is too long, regenerate a shorter one instead of truncating
            if len(tweet_text) > max_text_length - 5 and attempt < retries - 1:
                logger.warning(f"Tweet text too long ({len(tweet_text)} chars). Retrying...")
                time.sleep(base_delay * (attempt + 1))
                continue
                
            # Truncate as a last resort
            if len(tweet_text) > max_text_length - 5:
                tweet_text = tweet_text[:max_text_length - 8] + "..."
                
            # Add URL if available
            if url:
                tweet = f"{tweet_text} {url}"
            else:
                tweet = tweet_text
            
            # Generate 1-3 hashtags
            hashtag_count = random.randint(1, 3)
            hashtags = generate_relevant_hashtags(tweet_text, hashtag_count)
            hashtag_text = " ".join(hashtags) if hashtags else ""
            
            # Add hashtags if there's room, always at the very end
            if hashtag_text and len(tweet) + len(hashtag_text) + 1 <= 280:
                tweet = f"{tweet} {hashtag_text}"
                
            logger.info(f"Generated leak tweet ({len(tweet)} chars) for {title}")
            return tweet
            
        except Exception as e:
            logger.error(f"Error generating leak tweet (attempt {attempt+1}/{max_attempts}): {str(e)}")
            if attempt < max_attempts - 1:
                sleep_time = base_delay * (attempt + 1)
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Max retries reached for generating leak tweet")
                return None

def check_tweet_uniqueness(new_tweet, existing_tweets, similarity_threshold=0.6):
    """
    Check if a tweet is unique compared to existing tweets.
    Returns True if the tweet is unique (not similar to existing tweets),
    and False if it's too similar to an existing tweet.
    """
    if not new_tweet or not existing_tweets:
        return True
        
    # Normalize tweet for comparison (lowercase, remove URLs)
    def normalize_text(text):
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        # Convert to lowercase and strip whitespace
        return text.lower().strip()
    
    normalized_new = normalize_text(new_tweet)
    
    # Extract first 4 words to check for similar beginnings
    new_words = normalized_new.split()[:4]
    if len(new_words) < 3:  # Skip very short tweets
        return True
        
    new_beginning = ' '.join(new_words)
    
    for existing in existing_tweets:
        normalized_existing = normalize_text(existing)
        
        # Check if beginnings are too similar
        existing_words = normalized_existing.split()[:4]
        if len(existing_words) >= 3:
            existing_beginning = ' '.join(existing_words)
            
            # If first 3-4 words are identical, reject as too similar
            if new_beginning == existing_beginning:
                logger.warning(f"Tweet rejected - similar beginning: {new_beginning}")
                return False
            
            # Use difflib to check overall similarity
            import difflib
            similarity = difflib.SequenceMatcher(None, normalized_new, normalized_existing).ratio()
            
            if similarity >= similarity_threshold:
                logger.warning(f"Tweet rejected - {similarity:.2f} similar (threshold: {similarity_threshold})")
                return False
                
    return True

def generate_tweets(count=30, platform="both", large_pool_size=25, days_back=2):
    """
    Generate a specified number of tweets using different methods
    
    Args:
        count: Number of tweets to ultimately generate and return
        platform: Platform to generate tweets for ("both", "x", "twitter", "bluesky")
        large_pool_size: Size of the initial pool of tweets to generate before filtering
                         for uniqueness (default: 100)
        days_back: Number of days to look back for recent content (default: 2)
    """
    logger.info(f"Starting tweet generation: count={count}, platform={platform}, pool_size={large_pool_size}, days_back={days_back}")
    
    # Initialize metrics tracking
    metrics_tracker = None
    if METRICS_ENABLED:
        try:
            metrics_tracker = get_metrics_tracker()
            # Log the start of generation with parameters
            metrics_tracker.log_generation_start(
                pool_size=large_pool_size,
                uniqueness_threshold=0.6,  # Default threshold in check_tweet_uniqueness
                temperature_settings=TEMP_SETTINGS.copy()
            )
            logger.info("Metrics tracking enabled for this generation run")
        except Exception as e:
            logger.warning(f"Failed to initialize metrics tracking: {e}")
    
    # Load all existing tweets to check for uniqueness
    existing_tweets = load_existing_tweets()
    
    # Load a larger number of recent tweets for stronger similarity checking
    recent_tweets = []
    tweets_dir = os.path.join(BASE_DIR, "tweets")
    all_tweet_files = sorted([f for f in os.listdir(tweets_dir) 
                        if (f.startswith("x_tweets_") or f.startswith("bluesky_tweets_")) 
                        and f.endswith(".txt")], reverse=True)
    
    # Get content from 20 most recent tweet files
    for file in all_tweet_files[:20]:
        try:
            with open(os.path.join(tweets_dir, file), 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        recent_tweets.append(line.strip())
        except Exception as e:
            logger.warning(f"Error reading recent tweets from {file}: {e}")
    
    logger.info(f"Loaded {len(recent_tweets)} recent tweets for similarity checking during generation")
    
    # Combine all tweets for similarity checking
    all_tweets_for_comparison = existing_tweets + recent_tweets
    
    # Load content for tweet generation - using the specified days_back parameter
    logger.info(f"Loading articles and news items from the past {days_back} days")
    articles = load_articles(days_back=days_back)
    news_items = load_news_items(days_back=days_back)
    
    # Sort articles by random to prioritize different content each time
    random.shuffle(articles)
    
    # Weight the different types of tweets
    tweet_types = []
    
    # Try to get weights from config
    try:
        from config_loader import ConfigLoader
        config = ConfigLoader()
        article_weight = float(config.get_value("social.sharing.article_weight", "0.4"))
        news_weight = float(config.get_value("social.sharing.news_weight", "0.3"))
        commentary_weight = float(config.get_value("social.sharing.commentary_weight", "0.2"))
        creative_weight = float(config.get_value("social.sharing.creative_weight", "0.1"))
    except Exception as e:
        logger.warning(f"Could not load weights from config: {e}")
        article_weight = 0.4
        news_weight = 0.3
        commentary_weight = 0.2
        creative_weight = 0.1
    
    # If we have articles and news items, use a mix
    if articles and news_items:
        tweet_types = [
            {"type": "article", "weight": article_weight, "data": articles},
            {"type": "news_item", "weight": news_weight, "data": news_items},
            {"type": "commentary", "weight": commentary_weight, "data": None},
            {"type": "absurd_take", "weight": creative_weight, "data": None}
        ]
    # If we have only articles
    elif articles:
        tweet_types = [
            {"type": "article", "weight": article_weight + news_weight/2, "data": articles},
            {"type": "commentary", "weight": commentary_weight + news_weight/4, "data": None},
            {"type": "absurd_take", "weight": creative_weight + news_weight/4, "data": None}
        ]
    # If we have only news items
    elif news_items:
        tweet_types = [
            {"type": "news_item", "weight": news_weight + article_weight/2, "data": news_items},
            {"type": "commentary", "weight": commentary_weight + article_weight/4, "data": None},
            {"type": "absurd_take", "weight": creative_weight + article_weight/4, "data": None}
        ]
    # If we have neither, just generate random tweets
    else:
        tweet_types = [
            {"type": "commentary", "weight": 0.6, "data": None},
            {"type": "absurd_take", "weight": 0.4, "data": None}
        ]
    
    # Calculate cumulative weights for weighted random selection
    total_weight = sum(t["weight"] for t in tweet_types)
    tweet_types_cumulative = []
    cumulative = 0
    for t in tweet_types:
        cumulative += t["weight"] / total_weight
        tweet_types_cumulative.append((cumulative, t))
    
    # Generate a large pool of initial tweets
    initial_tweet_pool = []
    used_articles = set()
    used_leaks = set()
    
    # Track tweet types for metrics
    tweet_type_counts = {
        "article": 0,
        "news_item": 0,
        "commentary": 0,
        "absurd_take": 0
    }
    
    # Generate more tweets than needed (large_pool_size)
    logger.info(f"Generating initial pool of {large_pool_size} tweets to filter for uniqueness")
    attempts = 0
    max_attempts = large_pool_size * 3  # Allow for some failed attempts
    
    while len(initial_tweet_pool) < large_pool_size and attempts < max_attempts:
        attempts += 1
        
        # Randomly select a tweet type based on weights
        r = random.random()
        selected_type = None
        for cum_weight, tweet_type in tweet_types_cumulative:
            if r <= cum_weight:
                selected_type = tweet_type
                break
        
        tweet = None
        tweet_type = None
        
        if selected_type["type"] == "article" and articles:
            # Find an unused article
            available_articles = [a for a in articles if a["title"] not in used_articles]
            if not available_articles:
                # If we've used all articles, continue with other tweet types
                continue
            
            article = random.choice(available_articles)
            tweet = generate_article_summary_tweet(article)
            if tweet:
                used_articles.add(article["title"])
                tweet_type = "article"
                
        elif selected_type["type"] == "news_item" and news_items:
            # Find an unused news item
            available_news = [l for l in news_items if l.get("title") not in used_leaks]
            if not available_news:
                # If we've used all news items, continue with other tweet types
                continue
            
            news_item = random.choice(available_news)
            tweet = generate_news_tweet(news_item)
            if tweet:
                used_leaks.add(news_item.get("title"))
                tweet_type = "news_item"
                
        elif selected_type["type"] == "commentary":
            tweet = generate_commentary_tweet()
            if tweet:
                tweet_type = "commentary"
            
        elif selected_type["type"] == "absurd_take":
            tweet = generate_absurd_take_tweet()
            if tweet:
                tweet_type = "absurd_take"
        
        # Check if the tweet is valid, not a duplicate, and passes uniqueness check
        if tweet and tweet not in initial_tweet_pool:
            # Check uniqueness against existing tweets
            if check_tweet_uniqueness(tweet, all_tweets_for_comparison):
                initial_tweet_pool.append(tweet)
                # Increment type counter for metrics
                if tweet_type:
                    tweet_type_counts[tweet_type] = tweet_type_counts.get(tweet_type, 0) + 1
                logger.info(f"Generated unique tweet ({len(initial_tweet_pool)}/{large_pool_size}) of type: {tweet_type}")
            else:
                logger.info(f"Tweet failed uniqueness check, discarding")
    
    logger.info(f"Generated {len(initial_tweet_pool)} unique tweets from {attempts} attempts")
    
    # Sort the initial pool by estimated uniqueness (compare each tweet against all others)
    tweet_uniqueness_scores = []
    for i, tweet in enumerate(initial_tweet_pool):
        # Compare this tweet against all other tweets in the pool
        total_similarity = 0
        comparisons = 0
        
        for j, other_tweet in enumerate(initial_tweet_pool):
            if i == j:
                continue
                
            # Use the check_tweet_uniqueness function but extract just the similarity score
            import difflib
            # Normalize tweets for comparison
            def normalize_text(text):
                text = re.sub(r'https?://\S+', '', text)
                text = re.sub(r'#\w+', '', text)
                return text.lower().strip()
                
            similarity = difflib.SequenceMatcher(
                None, 
                normalize_text(tweet), 
                normalize_text(other_tweet)
            ).ratio()
            
            total_similarity += similarity
            comparisons += 1
        
        # Calculate average similarity to other tweets
        avg_similarity = total_similarity / comparisons if comparisons > 0 else 0
        # Convert to uniqueness score (lower similarity = higher uniqueness)
        uniqueness_score = 1 - avg_similarity
        
        tweet_uniqueness_scores.append((uniqueness_score, tweet))
    
    # Sort by uniqueness score (highest uniqueness first)
    tweet_uniqueness_scores.sort(reverse=True)
    
    # Take the most unique tweets up to the requested count
    final_count = min(count, len(tweet_uniqueness_scores))
    most_unique_tweets = [tweet for _, tweet in tweet_uniqueness_scores[:final_count]]
    
    # Final shuffle to ensure we're not creating patterns in the output
    random.shuffle(most_unique_tweets)
    
    logger.info(f"Selected {len(most_unique_tweets)} most unique tweets from pool of {len(initial_tweet_pool)}")
    
    # Tweet type counts were already tracked during generation
    
    # Update metrics with generation results
    if metrics_tracker:
        try:
            # Calculate number of duplicates filtered
            duplicates_filtered = attempts - len(initial_tweet_pool)
            
            # Log generation completion with statistics
            metrics_tracker.log_generation_complete(
                unique_tweets=len(most_unique_tweets),
                duplicates_filtered=duplicates_filtered,
                tweet_type_counts=tweet_type_counts
            )
            logger.info("Generation metrics recorded successfully")
        except Exception as e:
            logger.warning(f"Failed to record generation metrics: {e}")
    
    # Save tweets for the appropriate platform
    x_tweets = []
    bluesky_tweets = []
    
    for tweet in most_unique_tweets:
        if platform.lower() in ["both", "x", "twitter"]:
            x_tweets.append(tweet)
        if platform.lower() in ["both", "bluesky"]:
            bluesky_tweets.append(tweet)
    
    # Save tweets to files
    if x_tweets:
        x_file = save_tweets("x", x_tweets)
    if bluesky_tweets:
        bluesky_file = save_tweets("bluesky", bluesky_tweets)
    
    return most_unique_tweets

# Function no longer needed since we adjust the temperatures directly
# in the dictionary now

if __name__ == "__main__":
    # Try to get site name from config for help text
    try:
        from config_loader import ConfigLoader
        config = ConfigLoader()
        site_name = config.get_value("site.info.title", "your website")
        description = f"Generate tweets for {site_name}"
    except Exception:
        description = "Generate tweets for your website"
        
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--count", type=int, default=30, help="Number of tweets to generate")
    parser.add_argument("--platform", type=str, default="both", choices=["both", "x", "twitter", "bluesky"], help="Platform to generate tweets for")
    parser.add_argument("--creative", action="store_true", help="Use higher temperature for more creative content")
    parser.add_argument("--extraunique", action="store_true", help="Generate extra unique content with maximum variation")
    parser.add_argument("--pool-size", type=int, default=25, help="Size of the initial pool to generate (default: 25)")
    parser.add_argument("--debug", action="store_true", help="Show additional debug information")
    parser.add_argument("--days", type=int, default=2, help="Number of days to look back for content (default: 2)")
    args = parser.parse_args()
    
    # Set more verbose logging if debug mode is enabled
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled - showing additional diagnostic information")
    
    # Log basic information about the run
    logger.info(f"Starting tweet generation - Platform: {args.platform}, Count: {args.count}, Pool size: {args.pool_size}")
    logger.info(f"Looking back {args.days} days for recent content")
    
    # If creative mode is enabled, increase temperatures for more varied content
    if args.creative or args.extraunique:
        if args.extraunique:
            logger.info("Using MAXIMUM temperature for extremely unique and diverse content")
            temp_boost = 0.25  # Larger boost for extra unique content
            max_temp = 0.98    # Almost maximum randomness
        else:
            logger.info("Using higher temperature for more creative and diverse content")
            temp_boost = 0.15  # Standard creative boost
            max_temp = 0.95    # Standard creative max
        
        # Update the dictionary values
        for key in ["commentary", "article", "absurd", "leak"]:
            current_temp = TEMP_SETTINGS[key]
            TEMP_SETTINGS[key] = min(current_temp + temp_boost, max_temp)
        
        # Keep hashtag temperature the same (or slightly increase it for extraunique)
        if args.extraunique:
            TEMP_SETTINGS["hashtag"] = min(TEMP_SETTINGS["hashtag"] + 0.1, 0.9)  # Slightly more varied hashtags
            
        logger.info(f"Temperature settings: Commentary={TEMP_SETTINGS['commentary']}, Article={TEMP_SETTINGS['article']}, " +
                    f"Absurd={TEMP_SETTINGS['absurd']}, Leak={TEMP_SETTINGS['leak']}, Hashtag={TEMP_SETTINGS['hashtag']}")
    
    # Generate tweets with a large initial pool for better uniqueness filtering
    logger.info(f"Generating a pool of {args.pool_size} tweets to find {args.count} most unique ones...")
    
    # Capture start time for performance measurement
    start_time = time.time()
    
    tweets = generate_tweets(
        count=args.count, 
        platform=args.platform, 
        large_pool_size=args.pool_size,
        days_back=args.days
    )
    
    # Calculate and log generation time
    generation_time = time.time() - start_time
    logger.info(f"Tweet generation completed in {generation_time:.2f} seconds")
    
    # Print generated tweets
    for i, tweet in enumerate(tweets):
        print(f"\nTweet {i+1}:")
        print(f"{tweet}")
        print(f"Character count: {len(tweet)}")
        print("-" * 40)
    
    # Final summary
    logger.info(f"Generated {len(tweets)} tweets")
    logger.info("Tweet generation completed successfully")