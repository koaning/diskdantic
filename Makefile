.PHONY: install lint test publish clean

# Install dependencies using uv
install:
	uv venv --allow-existing
	uv sync --group dev
	uv run pre-commit install

# Run linting
lint:
	uv run pre-commit run --all-files

# Run tests
test:
	uv run pytest

# Publish to PyPI
publish:
	uv build
	uv publish

# Clean up build artifacts and caches
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
