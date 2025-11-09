.PHONY: install test publish clean

# Install dependencies using uv
install:
	uv venv --allow-existing
	uv pip install -e .
	uv pip install --group dev

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
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
