FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir uv
# Ensure uv runtime binaries are present (copy from upstream uv image)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Use uv to sync project dependencies into the image
RUN uv sync --no-managed-python --frozen --active || true && \
	pip install --no-cache-dir -r requirements.txt || true
EXPOSE 8501
ENV STREAMLIT_SERVER_ENABLECORS=false
# Use uv to run the Streamlit process in the container's environment
CMD ["uv","run","streamlit","run","app.py","--server.port","8501","--server.address","0.0.0.0"]
