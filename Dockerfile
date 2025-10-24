# Dockerfile Final
FROM python:3.10-bullseye
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential gcc
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "tkr_production_bot.py"]
