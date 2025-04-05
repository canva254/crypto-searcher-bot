# Automatic GitHub Synchronization

Your project is now set up with automatic GitHub synchronization. Any changes made in this Replit project will be automatically pushed to your GitHub repository.

## How It Works

1. **GitHub Actions Workflow**
   - Located in `.github/workflows/auto-sync.yml`
   - Runs every 15 minutes to pull changes from your Replit project

2. **Local Auto-Sync Script**
   - The file `replit-to-github-sync.sh` will continuously check for changes and push them to GitHub
   - It runs every 5 minutes and uses your GitHub token for authentication

## How to Use

To start the auto-sync process, run:

```bash
./replit-to-github-sync.sh
```

This will continuously monitor for changes and push them to GitHub. You can keep this running in a separate shell tab.

## Manual Pushing

If you prefer to push changes manually, you can still use:

```bash
git add .
git commit -m "Your commit message"
git push origin main
```

## Security Note

Your GitHub token is stored in the `replit-to-github-sync.sh` script. Make sure to keep this script private and not share it with others.
