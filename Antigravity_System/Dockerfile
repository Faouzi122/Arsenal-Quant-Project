FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir fastapi uvicorn httpx

# Copy repository contents
COPY . .

# Expose the gateway port
EXPOSE 8088

# Command to run the gateway server
CMD ["python", "06_Router_MCP/l402_gateway_real.py"]
