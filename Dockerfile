FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn httpx

COPY . .

EXPOSE 8088

CMD ["python", "06_Router_MCP/l402_gateway_real.py"]
