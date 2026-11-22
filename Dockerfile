# Lightweight Python 3.9 base image matching the Lab VM runtime
FROM python:3.9-slim

# Accept version tag at build time (default v2.0.1)
ARG APP_VERSION=v2.0.1

# Runtime configuration for containerized Flask and real-time logging
ENV APP_VERSION=${APP_VERSION} \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user for container security
RUN useradd -m aceestuser

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and templates
COPY . .

# Grant non-root user ownership so SQLite DB writes succeed cleanly
RUN chown -R aceestuser:aceestuser /app

USER aceestuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')" || exit 1

CMD ["python", "ACEest_Fitness.py"]
