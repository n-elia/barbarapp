BarbarApp (Streamlit)

Quick start

1. Create a Python venv and install dependencies:

```bash
# using `uv` (recommended)
uv venv create
uv sync --active


Run with uv

```bash
# Run the Streamlit app using uv-managed Python/environment
uv run streamlit run app.py

# Run a quick syntax check using uv-managed Python
uv run python -m py_compile app.py libs/**/*.py pages/**/*.py
```

Or use the provided convenience script:

```bash
./run_checks.sh
```
# Or with a plain venv and pip:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run locally:

```bash
streamlit run app.py
```

3. First run will prompt to create the initial admin user (first-run bootstrap).

Docker

```bash
docker build -t darts-planner .
docker run -p 8501:8501 -v $(pwd)/data:/app/data darts-planner
```

Data: the app uses SQLite at `data/data.db` by default.
