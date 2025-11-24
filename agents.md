# Agent Setup Guide

This document explains how to set up the development environment for diskdantic, with a focus on using `uv` for Python dependency management.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - An extremely fast Python package installer and resolver

## Quick Start

The project includes a Makefile with all common commands. To get started:

```bash
make install
```

This single command will:
1. Create a virtual environment (`.venv/`)
2. Install all project dependencies
3. Install development dependencies (pytest, ruff, pre-commit)
4. Set up pre-commit hooks

## Project Structure

The project uses modern Python packaging standards:

```
diskdantic/
├── pyproject.toml         # Project metadata and dependencies
├── Makefile               # Common development commands
├── diskdantic/            # Main package code
├── tests/                 # Test files
└── .venv/                 # Virtual environment (created by uv)
```

## Development Workflow

1. **First time setup:**
   ```bash
   make install
   ```

2. **Make your changes to the code**

3. **Run tests:**
   ```bash
   make test
   ```

4. **Check linting (automatically runs on commit):**
   ```bash
   make lint
   ```

5. **Commit your changes** (pre-commit hooks will run automatically)
