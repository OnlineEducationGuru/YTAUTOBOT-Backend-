FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    imagemagick \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p output/scripts output/audio output/videos output/thumbnails output/temp credentials data

EXPOSE 5000

CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --timeout 600 --workers 2
