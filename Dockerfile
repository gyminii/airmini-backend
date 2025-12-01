# --------------------------------------------------------
# 1. Base image
# --------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --------------------------------------------------------
# 2. System dependencies
# --------------------------------------------------------
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    libpq-dev \
    git \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------
# 3. Set working directory
# --------------------------------------------------------
WORKDIR /app

# --------------------------------------------------------
# 4. Install dependencies
# --------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m nltk.downloader -d /usr/local/share/nltk_data stopwords
ENV NLTK_DATA=/usr/local/share/nltk_data

# --------------------------------------------------------
# 5. Copy entire project
# --------------------------------------------------------
COPY . .

# --------------------------------------------------------
# 6. Expose API port
# --------------------------------------------------------
EXPOSE 8000

# --------------------------------------------------------
# 7. Start FastAPI server
# --------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
