#!/usr/bin/env python3
"""
Configuration Loader
This script loads XML configuration files and provides access to site settings.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("config_loader")

class ConfigLoader:
    """Loads and parses site configuration from XML files."""
    
    def __init__(self, config_dir: str = None):
        """Initialize the config loader.
        
        Args:
            config_dir: Path to the configuration directory. If None, looks for CONFIG_DIR 
                      environment variable, then falls back to default location.
        """
        # Determine the config directory location
        if config_dir is None:
            # Try environment variable first
            config_dir = os.environ.get("CONFIG_DIR")
            
            if config_dir is None:
                # Fall back to default: config/ dir in the same directory as the script
                config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        
        self.config_dir = config_dir
        self.configs = {}
        
        # Log the configuration directory
        logger.info(f"Configuration directory: {self.config_dir}")
        
        # Load the core configuration files
        self._load_core_configs()
    
    def _load_core_configs(self) -> None:
        """Load the core configuration files."""
        core_files = [
            "credentials.xml",  # Load credentials first to ensure they're available
            "site.xml",
            "navigation.xml",
            "social.xml"
        ]
        
        for filename in core_files:
            filepath = os.path.join(self.config_dir, filename)
            if os.path.exists(filepath):
                self._load_config(filename)
            else:
                logger.warning(f"Core config file not found: {filepath}")
                
        # After loading configs, try to populate missing credentials from environment variables
        self._load_credentials_from_env()
    
    def _load_config(self, filename: str) -> None:
        """Load a single configuration file.
        
        Args:
            filename: Name of the XML file to load (relative to config directory)
        """
        filepath = os.path.join(self.config_dir, filename)
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Extract the config type from the filename
            config_type = os.path.splitext(os.path.basename(filename))[0]
            
            # If the file is in a subdirectory, include the subdirectory in the type
            if os.path.dirname(filename):
                config_type = os.path.dirname(filename).replace('/', '_') + '_' + config_type
            
            # Convert XML to dictionary
            config_data = self._xml_to_dict(root)
            
            # Store the config
            self.configs[config_type] = config_data
            logger.info(f"Loaded config: {config_type}")
        except Exception as e:
            logger.error(f"Error loading config {filename}: {e}")
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert an XML element to a dictionary recursively.
        
        Args:
            element: XML element to convert
            
        Returns:
            Dictionary representation of the XML
        """
        result = {}
        
        # Handle child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            
            if child.tag in result:
                # If this tag already exists, convert to a list or append to existing list
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                # First occurrence of the tag
                if child.attrib and len(child) == 0:
                    # Element with attributes and no children - combine text and attributes
                    if child.text and child.text.strip():
                        child_data['text'] = child.text.strip()
                    result[child.tag] = {**child_data, **child.attrib}
                elif not child_data and child.text and child.text.strip():
                    # Simple element with text
                    result[child.tag] = child.text.strip()
                else:
                    # Element with children or attributes
                    if child.attrib:
                        # If it has attributes, ensure they're included
                        result[child.tag] = {**child_data, **{'@' + k: v for k, v in child.attrib.items()}}
                    else:
                        result[child.tag] = child_data
        
        # Handle attributes of the current element
        for key, value in element.attrib.items():
            result['@' + key] = value
        
        # Handle text of the current element
        if element.text and element.text.strip() and not result:
            text = element.text.strip()
            if text and not list(element):  # If there are no child elements
                return text
        
        return result
    
    def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get a specific configuration by type.
        
        Args:
            config_type: Type of configuration to retrieve (e.g., 'site', 'navigation')
            
        Returns:
            Configuration dictionary
        """
        if config_type not in self.configs:
            # Try to load the config if it's not already loaded
            self._load_config(f"{config_type}.xml")
        
        return self.configs.get(config_type, {})
    
    def get_prompt(self, prompt_type: str) -> Dict[str, Any]:
        """Get a specific prompt configuration.
        
        Args:
            prompt_type: Type of prompt to retrieve (e.g., 'news', 'tweets')
            
        Returns:
            Prompt configuration dictionary
        """
        prompt_path = os.path.join("prompts", f"{prompt_type}.xml")
        
        if f"prompts_{prompt_type}" not in self.configs:
            # Try to load the prompt config if it's not already loaded
            self._load_config(prompt_path)
        
        return self.configs.get(f"prompts_{prompt_type}", {})
    
    def get_keywords(self, keyword_type: str) -> Dict[str, Any]:
        """Get keywords by type.
        
        Args:
            keyword_type: Type of keywords to retrieve (e.g., 'primary', 'trending')
            
        Returns:
            Keywords configuration dictionary
        """
        keyword_path = os.path.join("keywords", f"{keyword_type}.xml")
        
        if f"keywords_{keyword_type}" not in self.configs:
            # Try to load the keywords config if it's not already loaded
            self._load_config(keyword_path)
        
        return self.configs.get(f"keywords_{keyword_type}", {})

    def get_value(self, path: str, default: Any = None) -> Any:
        """Get a specific configuration value using dot notation path.
        
        Args:
            path: Path to the configuration value (e.g., 'site.info.title')
            default: Default value to return if the path doesn't exist
            
        Returns:
            Configuration value or default
        """
        # Split the path
        parts = path.split('.')
        
        if len(parts) < 2:
            return default
        
        # Get the config type
        config_type = parts[0]
        
        # Get the config
        config = self.get_config(config_type)
        
        # Navigate to the requested value
        current = config
        for part in parts[1:]:
            if not current or not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        
        return current
    
    def get_keywords_list(self, category: str, keyword_type: str = "primary") -> List[str]:
        """Get keywords for a specific category as a list.
        
        Args:
            category: Category of keywords to retrieve (e.g., 'core_topics', 'key_people')
            keyword_type: Type of keywords to use (e.g., 'primary', 'trending')
            
        Returns:
            List of keywords
        """
        keywords_config = self.get_keywords(keyword_type)
        
        if not keywords_config or 'category' not in keywords_config:
            return []
        
        # Handle case where categories is a list
        categories = keywords_config.get('category', [])
        if not isinstance(categories, list):
            categories = [categories]
        
        # Find the right category
        for cat in categories:
            if isinstance(cat, dict) and cat.get('@name') == category:
                # Get the keywords from this category
                keywords = cat.get('keyword', [])
                if not isinstance(keywords, list):
                    keywords = [keywords]
                return keywords
        
        return []
    
    def get_prompt_text(self, prompt_type: str, prompt_name: str) -> str:
        """Get a prompt text by type and name.
        
        Args:
            prompt_type: Type of prompt (e.g., 'news', 'tweets')
            prompt_name: Name of the prompt (e.g., 'system_prompt', 'user_prompt')
            
        Returns:
            Prompt text or empty string if not found
        """
        prompts = self.get_prompt(prompt_type)
        
        if not prompts or prompt_name not in prompts:
            return ""
        
        return prompts.get(prompt_name, "")
    
    def process_template(self, template: str, variables: Dict[str, Any] = None) -> str:
        """Process a template string by replacing variables.
        
        Args:
            template: Template string with {{variable}} placeholders
            variables: Dictionary of variables to use for replacement
            
        Returns:
            Processed template with variables replaced
        """
        if variables is None:
            variables = {}
        
        # Regular expression to match {{variable}} pattern
        pattern = r'{{([\w\.]+)}}'
        
        # Function to replace matches with values
        def replacer(match):
            var_name = match.group(1)
            
            # Check if it's a direct variable from the provided dict
            if var_name in variables:
                return str(variables[var_name])
            
            # Check if it's a config path (contains dots)
            if '.' in var_name:
                return str(self.get_value(var_name, f"{{{{ {var_name} }}}}"))
            
            # Return the placeholder unchanged if not found
            return f"{{{{ {var_name} }}}}"
        
        # Replace all matched variables
        return re.sub(pattern, replacer, template)
    
    def load_template_file(self, filepath: str) -> str:
        """Load a template file and return its content.
        
        Args:
            filepath: Path to the template file
            
        Returns:
            Template content as string
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading template file {filepath}: {e}")
            return ""
    
    def process_template_file(self, filepath: str, variables: Dict[str, Any] = None) -> str:
        """Load and process a template file.
        
        Args:
            filepath: Path to the template file
            variables: Dictionary of variables to use for replacement
            
        Returns:
            Processed template with variables replaced
        """
        template = self.load_template_file(filepath)
        return self.process_template(template, variables)


# Example usage
if __name__ == "__main__":
    # Create a config loader
    config = ConfigLoader()
    
    # Get the site information
    site_info = config.get_config("site")
    if site_info and 'info' in site_info:
        print("\nSite Information:")
        print(f"Title: {config.get_value('site.info.title', 'Default Title')}")
        print(f"Description: {config.get_value('site.info.description', 'Default Description')}")
    
    # Get the navigation
    navigation = config.get_config("navigation")
    if navigation and 'menu' in navigation:
        menu = navigation['menu']
        if isinstance(menu, list):
            print("\nNavigation Menu:")
            for menu_item in menu:
                if isinstance(menu_item, dict) and '@type' in menu_item and menu_item.get('@type') == 'main':
                    items = menu_item.get('item', [])
                    if not isinstance(items, list):
                        items = [items]
                    for item in items:
                        if isinstance(item, dict) and 'title' in item and 'url' in item:
                            print(f"- {item['title']} -> {item['url']}")
        
    # Get keywords
    print("\nKeywords:")
    core_topics = config.get_keywords_list('core_topics')
    print(f"Core Topics: {', '.join(core_topics)}")
    
    # Example of template processing
    template = "Welcome to {{site.info.title}} - {{site.info.tagline}}"
    processed = config.process_template(template)
    print(f"\nProcessed Template: {processed}")