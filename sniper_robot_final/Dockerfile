# Dockerfile Final pour la Production

# Utiliser une image Python complète pour une meilleure compatibilité
FROM python:3.10-bullseye

# Définir le répertoire de travail
WORKDIR /app

# Installer les outils de construction système
RUN apt-get update && apt-get install -y build-essential gcc

# Mettre à jour pip et installer les librairies Python
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code du robot
COPY . .

# Définir la commande de démarrage
CMD ["python3", "daytrader_production.py"]
