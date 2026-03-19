# Contributing

Thank you for your interest in contributing to Telegram MCP Server.

## Prerequisites

- Python 3.10 or later
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/proshangite-x/telegram-mcp-server.git
   cd telegram-mcp-server
   ```

2. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. Install in development mode with dev dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

4. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

## Running Tests

```bash
pytest tests/ -v
```

## Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting:

```bash
ruff check .
```

## Pull Request Guidelines

1. Fork the repository and create your branch from `main`.
2. If you've added new functionality, add corresponding tests.
3. Ensure `pytest` passes and `ruff check .` reports no errors.
4. Update the README if you've added or changed tools.
5. Add an entry to `CHANGELOG.md` under `[Unreleased]`.
6. Keep commits focused — one logical change per commit.

## Code Style

- Use descriptive function and variable names.
- Add type hints to function signatures.
- Use docstrings for all public functions.
- Keep lines under 120 characters.

## Reporting Issues

Use the [issue tracker](https://github.com/proshangite-x/telegram-mcp-server/issues) with the provided templates. Include your Python version, OS, and any relevant error output.
