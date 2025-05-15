#!/bin/bash
# Script to commit the tweet metrics changes to the website template repository

# Navigate to website template directory (this should be run from that directory)
cd "$(dirname "$0")"

# Add all the new files
git add .github/workflows/post_to_twitter.yml
git add .github/workflows/post_to_bluesky.yml
git add scripts/tweet_metrics.py
git add scripts/generate_tweets.py
git add scripts/post_tweets.py
git add scripts/post_to_bluesky.py
git add scripts/post_to_x.py
git add requirements.txt

# Create metrics directories if they don't exist
mkdir -p metrics/graphs

# Commit the changes
git commit -m "Add tweet metrics tracking system with staggered posting workflows"

# Push the changes (uncomment if you want to push immediately)
# git push origin main

echo "Changes committed. Run 'git push origin main' to push them to the remote repository."