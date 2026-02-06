# BarbarApp — Darts Planner

A small Streamlit application to plan matches and track attendance.

## Setup

### Prerequisites

Install `uv` and `task` (one-time setup):

```bash
# Install uv (Python package manager and environment tool)
python -m pip install --upgrade pip
python -m pip install uv

# Install task (task runner; see https://taskfile.dev/)
# On macOS with Homebrew:
brew install go-task

# On Linux, or other systems:
# Download from https://taskfile.dev/installation/
```

After installing `task`, verify you can run tasks:
```bash
task --list
```

## Development workflow

All common development tasks are available through the `Taskfile.yml`. Use these commands to manage the project:

| Task | Description |
|------|-------------|
| `task run` | Run the Streamlit app (dev mode) |
| `task build` | Run quick project build checks: syntax, optional lint |
| `task build-image` | Build Docker image tagged `barbarapp:latest` |
| `task run-image` | Run Docker image (exposes port 8501) |
| `task reset-db` | Reset the SQLite database (delete and reinitialize) |
| `task show-db` | Quick check of DB tables (requires `sqlite3` CLI) |

### Quick start

```bash
# Sync dependencies (runs automatically on first `task` invocation, but can be run explicitly)
uv sync

# Run the app locally
task run
```

The app will be available at `http://localhost:8501`.

## First-run bootstrap

On first run, if there are no users in the database you will be prompted to create an initial administrator account. This bootstrap flow is handled in `views/login.py`.

## Database

- Default SQLite database: `data/data.db` (created automatically).
- Database is initialized on app startup (`libs/db.py` → `init_db()`).
- Use `task reset-db` to delete and reinitialize the database.
- Use `task show-db` to list all tables (requires `sqlite3` CLI installed).

## Docker

Build and run the app in a container:

```bash
# Build the Docker image
task build-image

# Run the container (maps port 8501 and persists data)
task run-image
```

The image is tagged as `barbarapp:latest` and includes `uv` to sync dependencies from `pyproject.toml`.

## Project info

- **Python version**: >= 3.11 (as specified in `pyproject.toml`)
- **Dependencies**: Declared in `pyproject.toml` under `[project].dependencies`
- **Dependency manager**: `uv` (https://docs.astral.sh/uv/)
- **Task runner**: `task` (https://taskfile.dev/)

---

For questions or to report issues, please open an issue or submit a PR. 🎯
