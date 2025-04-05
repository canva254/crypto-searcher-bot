# IDE Settings for Local Development

## Visual Studio Code

For optimal development experience in VS Code, add these settings to your workspace:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.analysis.extraPaths": [
        "${workspaceFolder}"
    ],
    "[python]": {
        "editor.rulers": [
            88
        ]
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/*.pyc": true
    }
}
```

## Setup a Local Environment

1. Create a virtual environment
2. Activate the environment
3. Install dependencies from pyproject.toml
4. Configure your environment variables
5. Run the application with python main.py
