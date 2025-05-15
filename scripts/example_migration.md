# Example Script Migration Guide

This guide shows how to convert a hardcoded script from Signal Leaks to use the template's configuration system.

## Original Script Example (From Signal Leaks)

```python
#!/usr/bin/env python3
# This script generates breaking news articles

from openai import OpenAI
import requests
import datetime
import os
import re
import time
import random

# Hardcoded API key
OPENAI_API_KEY = 'sk-proj-xxxxx'

# Hardcoded site info
SITE_TITLE = "Signal Leaks"
SITE_TAGLINE = "Truth and Transparency"

# Hardcoded keywords
KEY_PEOPLE = ["Pentagon", "White House", "Trump", "CIA", "Hegseth", "Vance"]
TOPICS = ["leaks", "government", "classified", "documents"]

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_article(topic=None):
    """Generate a breaking news article"""
    if not topic:
        topic = random.choice(TOPICS)
    
    # Hardcoded prompt
    prompt = f"""
    Write a breaking news article for {SITE_TITLE} about {topic}.
    Include mentions of {', '.join(random.sample(KEY_PEOPLE, 2))}.
    Make it sound serious but slightly absurd.
    Format as markdown with a headline.
    """
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"You are a writer for {SITE_TITLE}, a satirical news site."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].message.content

# Main function
if __name__ == "__main__":
    article = generate_article()
    print(article)
    
    # Save to file
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"Breaking_News_{timestamp}.md"
    with open(os.path.join("content", "news", filename), "w") as f:
        f.write(article)
```

## Migrated Script Using Template Configuration

```python
#!/usr/bin/env python3
# This script generates breaking news articles using the template configuration

import os
import sys
import datetime
import random
from pathlib import Path

# Import the config loader from the template
from config_loader import ConfigLoader

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI package not available. Install with: pip install openai")

# Set up base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")

def generate_article(config, topic=None):
    """Generate a breaking news article using configuration"""
    if not OPENAI_AVAILABLE:
        print("OpenAI not available. Cannot generate article.")
        return ""
    
    # Load site info from config
    site_title = config.get_value("site.info.title", "Website")
    site_tagline = config.get_value("site.info.tagline", "")
    
    # Load keywords from config
    key_people = config.get_keywords_list("key_people")
    topics = config.get_keywords_list("core_topics")
    
    # Use topic parameter or random topic from config
    if not topic and topics:
        topic = random.choice(topics)
    
    # Get API key from config
    api_key = config.get_value("social.openai.api_key")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("No OpenAI API key found.")
            return ""
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Get prompt template from config or use default
    system_prompt = config.get_prompt_text("news", "system_prompt")
    user_prompt = config.get_prompt_text("news", "user_prompt")
    
    # Use default prompts if not found in config
    if not system_prompt:
        system_prompt = f"You are a writer for {site_title}, a satirical news site."
    
    if not user_prompt:
        user_prompt = f"""
        Write a breaking news article for {site_title} about {topic}.
        Include mentions of {', '.join(random.sample(key_people, min(2, len(key_people))))} if possible.
        Make it sound serious but slightly absurd.
        Format as markdown with a headline.
        """
    
    # Process templates to replace variables
    variables = {
        "topic": topic,
        "key_people": ", ".join(random.sample(key_people, min(2, len(key_people)))) if key_people else "relevant people",
        "current_date": datetime.datetime.now().strftime("%Y-%m-%d")
    }
    
    user_prompt = config.process_template(user_prompt, variables)
    
    # Generate content
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].message.content

# Main function
if __name__ == "__main__":
    # Load configuration
    config = ConfigLoader(CONFIG_DIR)
    
    # Generate article
    article = generate_article(config)
    if not article:
        print("Failed to generate article.")
        sys.exit(1)
    
    print(article)
    
    # Save to file
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"Breaking_News_{timestamp}.md"
    
    # Get content directory from config or use default
    content_dir = config.get_value("content.directories.news", os.path.join("content", "news"))
    if not os.path.isabs(content_dir):
        content_dir = os.path.join(BASE_DIR, content_dir)
    
    # Create directory if it doesn't exist
    os.makedirs(content_dir, exist_ok=True)
    
    # Save file
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w") as f:
        f.write(article)
    
    print(f"Article saved to: {filepath}")
```

## Key Differences

1. **Configuration Loading**: The migrated script uses the `ConfigLoader` class to load settings from XML files instead of hardcoding values.

2. **Dynamic Keywords**: Keywords are loaded from the XML configuration instead of being hardcoded.

3. **API Key Management**: The OpenAI API key is retrieved from the configuration or environment variables.

4. **Template Processing**: Prompts are loaded from XML templates and can be customized without changing the script.

5. **Flexibility**: The migrated script can work with different site configurations without code changes.

6. **Error Handling**: The migrated script has better error checking and fallbacks.

## Migration Steps

1. **Identify Hardcoded Values**: Find all hardcoded values in the original script.

2. **Map to Configuration**: Determine where each value should be stored in the XML configuration.

3. **Replace Direct Access**: Change direct variable access to use the `config.get_value()` method.

4. **Add Fallbacks**: Always provide fallback values for configuration items.

5. **Use Templates**: Move string templates to the XML configuration.

6. **Add Error Handling**: Check for missing dependencies and configuration.

By following these steps, you can convert any script from Signal Leaks to use the templated configuration system.