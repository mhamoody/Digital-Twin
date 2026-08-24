FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts
RUN python -m pip install --upgrade pip && python -m pip install .

RUN useradd --create-home --uid 10001 digitaltwin
USER digitaltwin

CMD ["python", "-m", "uvicorn", "digital_twin.api.app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
