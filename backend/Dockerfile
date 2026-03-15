FROM python:3.11-slim

# Install system dependencies (minimal - no nodejs from apt)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from NodeSource (clean, minimal)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /storage/uploads /storage/skills /storage/artifacts

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
