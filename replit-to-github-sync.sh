#!/bin/bash

# GitHub Credentials
GITHUB_TOKEN="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"
GITHUB_USERNAME="canva254"
REPO_NAME="crypto-searcher-bot"

# Configure Git with token
git config --global credential.helper store
echo "https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

# Set Git identity
git config --global user.name "Replit Auto Sync"
git config --global user.email "${GITHUB_USERNAME}@users.noreply.github.com"

# Set remote URL with token
git remote set-url origin "https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo "Git configured with your GitHub token."
echo "Starting continuous sync process (press Ctrl+C to stop)..."

while true; do
  # Check for changes
  if [[ -n $(git status --porcelain) ]]; then
    echo "$(date): Changes detected!"
    
    # Stage all changes
    git add .
    
    # Commit changes
    git commit -m "Auto-sync: Updated from Replit at $(date)"
    
    # Push to GitHub
    if git push origin main; then
      echo "$(date): Successfully pushed changes to GitHub!"
    else
      echo "$(date): Failed to push changes. Will retry in 5 minutes."
    fi
  else
    echo "$(date): No changes detected."
  fi
  
  # Wait 5 minutes before checking again
  echo "Waiting for 5 minutes before next check..."
  sleep 300
done
