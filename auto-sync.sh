#!/bin/bash

# Set up Git
git config --global user.name "Auto Sync Bot"
git config --global user.email "bot@example.com"

while true; do
  # Check if there are changes
  if [[ -n $(git status --porcelain) ]]; then
    echo "Changes detected, committing and pushing..."
    git add .
    git commit -m "Auto-sync: Automatic commit from Replit"
    git push origin main
    echo "Changes pushed to GitHub!"
  else
    echo "No changes detected..."
  fi
  
  # Wait for 5 minutes before checking again
  echo "Waiting for 5 minutes before next check..."
  sleep 300
done
