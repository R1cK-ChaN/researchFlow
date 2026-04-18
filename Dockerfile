FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY config/ config/

RUN pip install --upgrade pip && pip install ".[service]"

EXPOSE 8000

CMD ["uvicorn", "researchflow.server.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-keep-alive", "300"]
