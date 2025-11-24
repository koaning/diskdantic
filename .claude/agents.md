# Project Setup: UV Package Manager

This project uses **uv** as the package manager for all Python operations.

## Running Commands

Always prefix Python commands with `uv run`:

```bash
# Run tests
uv run pytest

# Run linting
uv run pre-commit run --all-files

# Install dependencies
uv sync --group dev
```

## Key Commands

- **Install**: `uv venv --allow-existing && uv sync --group dev`
- **Test**: `uv run pytest`
- **Lint**: `uv run pre-commit run --all-files`
- **Format**: Automatically handled by pre-commit hooks

## Make Commands

The project has a Makefile with convenient shortcuts:

- `make install` - Set up environment
- `make test` - Run tests
- `make lint` - Run linters
- `make clean` - Clean build artifacts

All Makefile commands use `uv` internally.

## Git Commits

When committing code, pre-commit hooks will automatically run via uv. The hooks include:
- Ruff for linting and formatting
- Trailing whitespace fixes
- End of file fixes

Make sure all linting and formatting passes before committing.
