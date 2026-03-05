# Setup Guide

## Configuration

1. Copy the sample environment file to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update the `.env` file with your specific credentials and keys (e.g., API keys, database URLs).

## Local Development

If you're developing locally without Docker, you may need to start components individually:

1. **LLM Gateway**:
   ```bash
   cd poc/llm-gateway
   uvicorn app.main:app --reload --port 8000
   ```

2. **Hub**:
   ```bash
   cd poc/hub
   uvicorn app.main:app --reload --port 8001
   ```

## Running Tests

To run the test suite using pytest:

```bash
pytest
```

## VS Code

Open the project in VS Code. The `.vscode` configuration provided will recommend essential extensions (Python, Docker, Ruff) and setup code formatting automatically on save. Ensure you select the Virtual Environment (`.venv`) as your Python interpreter using `Ctrl+Shift+P` -> `Python: Select Interpreter`.
