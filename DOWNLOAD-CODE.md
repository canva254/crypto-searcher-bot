# Downloading Your Code from Replit

To download your crypto arbitrage bot code from Replit, follow these steps:

1. In the Replit interface, locate the "..." (three dots) menu in the left sidebar.

2. Click on it and select "Download as zip" from the dropdown menu.

3. Choose a location on your computer to save the ZIP file.

4. Extract the ZIP file to a folder on your computer.

The downloaded code will contain all your project files, including:

- Python source code (.py files)
- Templates for the web interface
- Static files (CSS, JavaScript)
- Configuration files
- Documentation files

## Important Notes

- Make sure to check that the `.env` file is not included in the ZIP (it contains sensitive API keys)
- You might need to create a new `.env` file on your local machine
- If you're planning to deploy this elsewhere, you'll need to set up a PostgreSQL database

## Using the Code Locally

After downloading, you'll need to:

1. Set up a Python virtual environment
2. Install the dependencies listed in `pyproject.toml`
3. Set up your environment variables as described in `.env.example`
4. Initialize the database

Refer to the README.md file for detailed setup instructions.
