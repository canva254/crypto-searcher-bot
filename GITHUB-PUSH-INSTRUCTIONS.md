# How to Push Your Code to GitHub

Since the direct push from Replit timed out, follow these steps to push your code to GitHub:

## Option 1: Using GitHub CLI (from your local machine)

1. Clone your Replit project first:
   ```
   git clone https://github.com/canva254/crypto-searcher-bot.git
   cd crypto-searcher-bot
   ```

2. Download your code from Replit (using the download option in the Replit interface)

3. Copy all files to your local repository folder

4. Add, commit and push the changes:
   ```
   git add .
   git commit -m "Initial commit from Replit"
   git push origin main
   ```

## Option 2: Using GitHub Personal Access Token

1. Create a personal access token on GitHub:
   - Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Generate a new token with "repo" permissions
   - Copy the generated token

2. Then run these commands in your Replit terminal:
   ```
   git remote set-url origin https://canva254:YOUR_PERSONAL_ACCESS_TOKEN@github.com/canva254/crypto-searcher-bot.git
   git push -u origin main
   ```

## Option 3: GitHub Desktop

1. Download your code from Replit
2. Use GitHub Desktop to push it to your repository

## Files to Exclude

Make sure these are in your .gitignore to avoid committing sensitive information:
- .env file (contains API keys)
- Instance folder 
- __pycache__ folders
