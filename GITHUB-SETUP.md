# GitHub Setup Instructions

To push this project to your GitHub repository, follow these steps:

## One-time Setup

1. Configure Git with your credentials:
   ```
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

2. Add your GitHub repository as a remote:
   ```
   git remote add origin https://github.com/YOUR_USERNAME/crypto-searcher-bot.git
   ```

3. Push the code to GitHub:
   ```
   git push -u origin main
   ```

## Using Personal Access Token (if password authentication fails)

If you encounter authentication issues, you may need to use a Personal Access Token (PAT):

1. Create a PAT on GitHub:
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Create a new token with "repo" permissions
   - Copy the generated token

2. Use the token for authentication:
   ```
   git remote add origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/YOUR_USERNAME/crypto-searcher-bot.git
   git push -u origin main
   ```

## Subsequent Pushes

After the initial setup, you can push changes with:
```
git add .
git commit -m "Your commit message"
git push
```

Remember to replace `YOUR_USERNAME` and `YOUR_TOKEN` with your actual GitHub username and personal access token.
