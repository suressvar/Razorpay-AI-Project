FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy pyproject.toml
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy backend source code
COPY src/ /app/src/
COPY tests/ /app/tests/

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "recovery_autopilot.main:app", "--host", "0.0.0.0", "--port", "8000"]
