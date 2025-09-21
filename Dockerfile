
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade pip
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

COPY src /app/src
COPY alembic /app/alembic

ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["python", "-m", "hamburgueria_bot.api.app"]
