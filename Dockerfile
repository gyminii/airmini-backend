FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    postgresql-client \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

RUN uv run playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["uv", "run", "--", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]