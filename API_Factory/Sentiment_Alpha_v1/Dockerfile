# © 2026 Meridian Alpha Systems - Intelligence & Logistics Division
# Watermark: ADSL-404-SIGMA
# Proprietary Container Image

FROM python:3.11-slim

WORKDIR /app

# Performance optimization: no-cache to keep the image minimal
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core engine source
COPY . /app

# Ensure persistent data directory exists
RUN mkdir -p /app/data

# Execute the Gateway
# (Server headers are obfuscated via internal middleware)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
