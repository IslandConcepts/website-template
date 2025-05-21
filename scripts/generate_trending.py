#!/usr/bin/env python3
"""
Trending Story Generator for CringeWorthy
This script generates sensational, tabloid-style articles based on trending topics
"""

import os
import sys
import argparse
from generate_stories import generate_trending_story

def main():
    """
    Main function to generate trending stories
    """
    parser = argparse.ArgumentParser(description='Generate trending stories for CringeWorthy')
    parser.add_argument('--section', type=str, choices=['shame', 'recent', 'lore', 'all'], 
                        default='all', help='Section to generate content for')
    parser.add_argument('--sample', action='store_true', help='Use sample content instead of OpenAI')
    parser.add_argument('--verbose', action='store_true', help='Show detailed process information')
    args = parser.parse_args()
    
    if args.section == 'all':
        sections = ['shame', 'recent', 'lore']
    else:
        sections = [args.section]
    
    results = []
    for section in sections:
        print(f"\nGenerating trending content for {section} section...")
        result = generate_trending_story(section, use_sample=args.sample)
        results.append(result)
        print(f"Generated article: {result}\n")
    
    print("Content generation complete!")
    
    # Print summary of all generated articles
    print("\n=== GENERATED ARTICLES SUMMARY ===")
    for i, result in enumerate(results):
        print(f"{i+1}. {result}")
    
if __name__ == "__main__":
    main()