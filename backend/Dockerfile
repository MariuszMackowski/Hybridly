FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN mkdir app && pip install --no-cache-dir -e ".[dev]"
COPY . .
CMD ["sh", "./entrypoint.sh"]
