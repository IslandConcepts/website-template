#!/usr/bin/env python3
"""
Content Generator
This script generates various types of content based on site configuration.
"""

import os
import sys
import argparse
import json
import time
import datetime
import re
import random
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional, Tuple

# Import the config loader
from config_loader import ConfigLoader

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI package not available. Install with: pip install openai")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("content_generator")

class ContentGenerator:
    """Generates content for the website based on configuration."""
    
    def __init__(self, config_dir: str = None):
        """Initialize the content generator.
        
        Args:
            config_dir: Path to the configuration directory (passed to ConfigLoader)
        """
        # Load configuration
        self.config = ConfigLoader(config_dir)
        
        # Get base directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Initialize OpenAI client if available
        self.client = None
        if OPENAI_AVAILABLE:
            # Try to get API key from environment first, then fall back to config
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                # Try to get from config
                api_key = self.config.get_value("social.openai.api_key")
            
            if api_key:
                self.client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OpenAI API key not found. Set OPENAI_API_KEY env var or in social.xml config.")
    
    def generate_article(self, article_type: str = "news", topic: str = None) -> Dict[str, Any]:
        """Generate an article based on configuration.
        
        Args:
            article_type: Type of article to generate (e.g., 'news', 'post')
            topic: Optional topic for the article
            
        Returns:
            Dictionary with the generated article data
        """
        # Check if OpenAI is available
        if not OPENAI_AVAILABLE or not self.client:
            logger.error("OpenAI not available. Cannot generate article.")
            return {"error": "OpenAI not available"}
        
        # Get site info for variables
        site_title = self.config.get_value("site.info.title", "Website")
        site_tagline = self.config.get_value("site.info.tagline", "")
        site_mission = self.config.get_value("site.info.description", "")
        
        # Get the key people and topics from keywords
        key_people = self.config.get_keywords_list("key_people")
        core_topics = self.config.get_keywords_list("core_topics")
        
        # If topic is not provided, select randomly from core topics
        if not topic and core_topics:
            topic = random.choice(core_topics)
        
        # Get prompt templates
        system_prompt_template = self.config.get_prompt_text(article_type, "system_prompt")
        user_prompt_template = self.config.get_prompt_text(article_type, "user_prompt")
        
        # If prompts not found, use defaults
        if not system_prompt_template:
            system_prompt_template = "You are a content writer for {{site.info.title}}. Create content that is informative and engaging."
        
        if not user_prompt_template:
            user_prompt_template = "Write an article about {{topic}} in the style of {{site.info.title}}."
        
        # Prepare variables for template processing
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Make sure all variables are safe by replacing double quotes
        if topic:
            topic = topic.replace('"', "'")
            
        safe_key_people = [person.replace('"', "'") for person in key_people] if key_people else []
        random_key_person = random.choice(safe_key_people) if safe_key_people else "relevant people"
        
        sample_size = min(3, len(safe_key_people))
        key_people_sample = random.sample(safe_key_people, sample_size) if safe_key_people else ["relevant figures"]
        key_people_str = ", ".join(key_people_sample)
        
        variables = {
            "topic": topic,
            "system_role_description": f"content writer for {site_title}",
            "content_tone": "informative",
            "content_style": "engaging",
            "site_mission": site_mission.replace('"', "'") if site_mission else "",
            "writing_style": "journalistic",
            "tone_adjective": "professional",
            "detail_level": "moderate",
            "site_voice": f"{site_title}'s unique voice",
            "target_audience": "general readers interested in current events",
            "article_length": "medium",
            "article_topic": topic if topic else "current events",
            "key_element_1": f"Include mention of {random_key_person}",
            "key_element_2": "Include a surprising fact or detail",
            "key_element_3": "End with a forward-looking statement",
            "key_people": key_people_str,
            "focus_area": topic if topic else "current developments",
            "current_date": current_date,
            "site_tone": "informative yet slightly satirical",
        }
        
        # Process templates
        system_prompt = self.config.process_template(system_prompt_template, variables)
        user_prompt = self.config.process_template(user_prompt_template, variables)
        
        # Add specific instruction about avoiding double quotes
        system_prompt += " IMPORTANT: Do not use double quotes in your content as they can break the formatting. Use single quotes instead if needed."
        
        # Log prompts for debugging
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"User Prompt: {user_prompt}")
        
        # Generate content using OpenAI
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 for high-quality content
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Process the content to extract title and body
            title, body = self._extract_title_and_body(content)
            
            # Replace any double quotes in the title and body
            title = title.replace('"', "'")
            
            # Create a short summary (for frontmatter)
            summary = body[:150].replace('"', "'") + "..."
            
            # Create a short title version if the title is long
            short_title = title
            if len(title) > 50:
                short_title = title[:47].replace('"', "'") + "..."
                
            # Generate a timestamped filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            filename = f"{safe_title}_{timestamp}.md"
            
            # Prepare the article data
            article = {
                "title": title,
                "shortTitle": short_title,
                "summary": summary,
                "content": body,
                "filename": filename,
                "date": current_date,
                "type": article_type,
                "topic": topic,
                "timestamp": timestamp
            }
            
            return article
            
        except Exception as e:
            logger.error(f"Error generating article: {e}")
            return {"error": str(e)}
    
    def _extract_title_and_body(self, content: str) -> Tuple[str, str]:
        """Extract title and body from generated content.
        
        Args:
            content: Generated content string
            
        Returns:
            Tuple of (title, body)
        """
        # Try to extract title (assumes markdown format with # Title)
        lines = content.strip().split('\n')
        title = ""
        body = content
        
        # Look for title in first line
        if lines and lines[0].startswith('#'):
            title = lines[0].lstrip('#').strip()
            body = '\n'.join(lines[1:]).strip()
        elif len(lines) > 1:
            # If no markdown title, use first line as title
            title = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
        
        return title, body
    
    def save_article(self, article: Dict[str, Any], output_dir: str = None) -> str:
        """Save the generated article to file.
        
        Args:
            article: Article data dictionary
            output_dir: Directory to save the article in (defaults to content/[type])
            
        Returns:
            Path to the saved file
        """
        if "error" in article:
            logger.error(f"Cannot save article with error: {article['error']}")
            return ""
        
        # Determine output directory
        if not output_dir:
            article_type = article.get("type", "posts")
            output_dir = os.path.join(self.base_dir, "content", article_type)
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        filename = article.get("filename", f"article_{article.get('timestamp', '')}.md")
        filepath = os.path.join(output_dir, filename)
        
        # Escape quotes in title and content to prevent frontmatter issues
        safe_title = article['title'].replace('"', '\\"')
        safe_short_title = article.get('shortTitle', safe_title).replace('"', '\\"')
        safe_summary = article.get('summary', '').replace('"', '\\"')
        
        # Generate tweet if it doesn't exist
        tweet = article.get('tweet', '')
        if not tweet:
            tweet = self.generate_social_post(article)
            article['tweet'] = tweet
        safe_tweet = tweet.replace('"', '\\"')
        
        # Prepare frontmatter
        frontmatter = [
            "---",
            f"title: \"{safe_title}\"",
            f"date: {article.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))}",
            f"draft: false",
            f"shortTitle: \"{safe_short_title}\"",
            f"summary: \"{safe_summary}\"",
            f"tweet: \"{safe_tweet}\""
        ]
        
        # Add optional frontmatter - integrate with generate_stories.py approach
        if "topic" in article and article["topic"]:
            # Clean up topic for tag
            safe_topic = article['topic'].replace('"', "'")
            # Extract main topic word if it's a complex topic with instructions
            if "TONE:" in safe_topic:
                main_topic = safe_topic.split()[0].upper()
            else:
                main_topic = safe_topic.upper()
            frontmatter.append(f"tags:")
            frontmatter.append(f"  - \"{main_topic}\"")
            frontmatter.append(f"  - \"CRINGE\"")
        
        frontmatter.append("---")
        
        # Combine frontmatter and content
        full_content = "\n".join(frontmatter) + "\n\n" + article["content"]
        
        # Write to file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info(f"Article saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return ""
    
    def generate_social_post(self, article: Dict[str, Any] = None, post_type: str = "twitter") -> str:
        """Generate a social media post, optionally based on an article.
        
        Args:
            article: Optional article data to base the post on
            post_type: Type of social post (twitter, bluesky, etc.)
            
        Returns:
            Generated social media post text
        """
        # Check if OpenAI is available
        if not OPENAI_AVAILABLE or not self.client:
            logger.error("OpenAI not available. Cannot generate social post.")
            return ""
        
        # Get prompt template
        prompt_template = self.config.get_prompt_text("social", f"{post_type}_prompt")
        
        # If prompt not found, use default
        if not prompt_template:
            prompt_template = "Create a short, engaging post for {{platform}} about {{topic}}."
        
        # Prepare variables
        site_title = self.config.get_value("site.info.title", "Website")
        
        variables = {
            "platform": post_type,
            "site_title": site_title,
            "max_length": "280" if post_type == "twitter" else "300",
        }
        
        # Add article-specific variables if available
        if article:
            # Create a safe summary without quotes that could break templates
            summary = article.get("content", "")[:200].replace('"', "'") + "..."
            
            variables.update({
                "article_title": article.get("title", "").replace('"', "'"),
                "article_summary": summary,
                "article_link": f"/{article.get('type', 'posts')}/{article.get('filename', '').replace('.md', '')}",
                "topic": article.get("topic", "").replace('"', "'"),
            })
        else:
            # Get random topic from keywords
            topics = self.config.get_keywords_list("core_topics")
            variables["topic"] = random.choice(topics).replace('"', "'") if topics else "current events"
        
        # Process template
        prompt = self.config.process_template(prompt_template, variables)
        
        # Add specific instructions to avoid quotes in the generated text
        prompt += "\n\nIMPORTANT: Do not use double quotes in your response as they can break my systems. Use single quotes instead if needed."
        
        # Generate post using OpenAI
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use GPT-3.5 for social posts (faster, cheaper)
                messages=[
                    {"role": "system", "content": f"You are a social media manager for {site_title}. Never use double quotes in your posts, only use single quotes if necessary."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            post_text = response.choices[0].message.content.strip()
            
            # Replace any remaining double quotes with single quotes
            post_text = post_text.replace('"', "'")
            
            # Ensure the post is within platform limits
            max_length = int(variables["max_length"])
            if len(post_text) > max_length:
                post_text = post_text[:max_length-3] + "..."
            
            return post_text
            
        except Exception as e:
            logger.error(f"Error generating social post: {e}")
            return ""
    
    def generate_content_batch(self, count: int = 1, types: List[str] = None) -> List[Dict[str, Any]]:
        """Generate a batch of content.
        
        Args:
            count: Number of pieces of content to generate
            types: List of content types to generate (e.g., ['news', 'post'])
            
        Returns:
            List of generated content items
        """
        if not types:
            types = ["news"]
            
        # Import generate_trending_story here to avoid circular imports
        try:
            from generate_stories import generate_trending_story
            trending_story_available = True
        except ImportError:
            logger.warning("generate_stories module not available, falling back to standard generation")
            trending_story_available = False
            
        results = []
        for i in range(count):
            content_type = random.choice(types)
            logger.info(f"Generating content {i+1}/{count} of type {content_type}")
            
            # For certain content types, use the specialized trending story generator
            if trending_story_available and content_type in ["shame", "recent", "lore"]:
                try:
                    # Use the trending story generator
                    logger.info(f"Using trending story generator for {content_type}")
                    filepath = generate_trending_story(content_type)
                    
                    # Extract filename for social posting
                    filename = os.path.basename(filepath)
                    title = filename.replace("_", " ").rsplit("_", 1)[0]
                    
                    # Create article data structure
                    article = {
                        "title": title,
                        "content": f"Generated using trending story generator",
                        "filename": filename,
                        "filepath": filepath,
                        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "type": content_type,
                        "topic": "trending",
                        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    }
                    
                    # Generate a social post for the article
                    social_post = self.generate_social_post(article)
                    article["tweet"] = social_post
                    article["social_post"] = social_post
                    
                    results.append(article)
                except Exception as e:
                    logger.error(f"Failed to generate trending story: {e}, falling back to standard generation")
                    # Fall back to standard generation
                    self._generate_standard_article(content_type, results)
            else:
                # Standard article generation
                self._generate_standard_article(content_type, results)
        
        return results
        
    def _generate_standard_article(self, content_type, results):
        """Helper method to generate a standard article"""
        article = self.generate_article(content_type)
        if "error" not in article:
            # Save the article
            filepath = self.save_article(article)
            article["filepath"] = filepath
            
            # Generate a social post for the article
            social_post = self.generate_social_post(article)
            article["tweet"] = social_post
            article["social_post"] = social_post
            
            results.append(article)
        else:
            logger.error(f"Failed to generate article: {article['error']}")


def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate content based on site configuration")
    parser.add_argument("--count", type=int, default=1, help="Number of pieces of content to generate")
    parser.add_argument("--type", type=str, default="news", help="Type of content to generate")
    parser.add_argument("--topic", type=str, help="Optional topic for content generation")
    parser.add_argument("--config-dir", type=str, help="Path to config directory")
    args = parser.parse_args()
    
    # Create content generator
    generator = ContentGenerator(args.config_dir)
    
    if args.count > 1:
        # Generate batch
        content_items = generator.generate_content_batch(args.count, [args.type])
        logger.info(f"Generated {len(content_items)} items")
        
        # Print a summary
        for i, item in enumerate(content_items):
            print(f"Item {i+1}: {item['title']} saved to {item['filepath']}")
            print(f"Social post: {item['social_post']}")
            print()
    else:
        # Generate single item
        article = generator.generate_article(args.type, args.topic)
        if "error" not in article:
            filepath = generator.save_article(article)
            print(f"Generated: {article['title']}")
            print(f"Saved to: {filepath}")
            
            # Generate social post
            social_post = generator.generate_social_post(article)
            print(f"Social post: {social_post}")
        else:
            print(f"Error: {article['error']}")


if __name__ == "__main__":
    main()