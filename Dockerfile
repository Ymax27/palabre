FROM python:3.12-slim AS builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim AS css

WORKDIR /src
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL -o /usr/local/bin/tailwindcss \
      https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 \
    && chmod +x /usr/local/bin/tailwindcss

COPY tailwind.config.js ./
COPY app/static/src.css ./app/static/src.css
COPY app/templates ./app/templates
RUN tailwindcss -i app/static/src.css -o app/static/app.css --minify

FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin palabre
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY --from=builder /install /usr/local
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY --from=css /src/app/static/app.css ./app/static/app.css

RUN chown -R palabre:palabre /app
USER palabre

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
