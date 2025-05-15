#!/usr/bin/env python3
"""
Template Processor
This script processes template files by replacing variables with values from the XML configuration.
"""

import os
import sys
import argparse
from pathlib import Path

# Import config loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from scripts.config_loader import ConfigLoader
except ImportError:
    print("Error: config_loader.py not found.")
    sys.exit(1)


def process_template_file(config, template_file, output_file, extra_vars=None):
    """
    Process a template file, replacing variables with values from configuration.

    Args:
        config: ConfigLoader instance
        template_file: Path to the template file
        output_file: Path where the processed file should be saved
        extra_vars: Additional variables to use for replacement
    """
    # Make sure the template file exists
    if not os.path.exists(template_file):
        print(f"Error: Template file {template_file} not found.")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Load the template
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading template file: {e}")
        return False
    
    # Process the template
    variables = extra_vars or {}
    processed_content = config.process_template(template_content, variables)
    
    # Save the processed file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        print(f"Successfully processed template and saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving processed file: {e}")
        return False


def process_directory(config, template_dir, output_dir, extra_vars=None):
    """
    Process all template files in a directory.

    Args:
        config: ConfigLoader instance
        template_dir: Directory containing template files
        output_dir: Directory where processed files should be saved
        extra_vars: Additional variables to use for replacement
    """
    if not os.path.exists(template_dir):
        print(f"Error: Template directory {template_dir} not found.")
        return False
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Process all files in the directory
    success_count = 0
    failure_count = 0
    
    for root, _, files in os.walk(template_dir):
        # Get relative path from template_dir
        rel_path = os.path.relpath(root, template_dir)
        
        for file in files:
            # Skip non-template files
            if file.startswith('.') or file.endswith('.pyc'):
                continue
            
            # Construct paths
            template_file = os.path.join(root, file)
            rel_file_path = os.path.join(rel_path, file) if rel_path != '.' else file
            output_file = os.path.join(output_dir, rel_file_path)
            
            # Make sure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Process the file
            if process_template_file(config, template_file, output_file, extra_vars):
                success_count += 1
            else:
                failure_count += 1
    
    print(f"Processed {success_count} files successfully, {failure_count} failures.")
    return failure_count == 0


def main():
    """Main function for the template processor script."""
    parser = argparse.ArgumentParser(description="Process template files by replacing variables with values from the XML configuration.")
    parser.add_argument("--template", required=True, help="Template file or directory to process")
    parser.add_argument("--output", required=True, help="Output file or directory for processed templates")
    parser.add_argument("--config-dir", help="Path to the configuration directory")
    parser.add_argument("--var", nargs=2, action="append", metavar=("NAME", "VALUE"), help="Additional variables to use for replacement")
    args = parser.parse_args()
    
    # Create config loader
    config = ConfigLoader(args.config_dir)
    
    # Parse additional variables
    extra_vars = {}
    if args.var:
        for name, value in args.var:
            extra_vars[name] = value
    
    # Check if template is a file or directory
    if os.path.isfile(args.template):
        # Process single file
        success = process_template_file(config, args.template, args.output, extra_vars)
    else:
        # Process directory
        success = process_directory(config, args.template, args.output, extra_vars)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()