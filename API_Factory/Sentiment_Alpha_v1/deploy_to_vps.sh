#!/bin/bash
set -e
# ==============================================================================
# © 2026 Meridian Alpha Systems - Logistics Division
# Ghost Protocol Deployment Script - V1.0 (Pure Logic Mode)
# ==============================================================================

# --- CONFIGURATION INFRASTRUCTURE ---
VPS_USER="root"
VPS_IP="199.247.19.249"
SSH_KEY="~/.ssh/id_rsa"
REMOTE_DIR="/home/faouzi/meridian_alpha_production"
ARCHIVE_NAME="meridian_alpha_release.tar.gz"

echo "[1/5] Initiating Ghost Scrubbing and Packaging..."

# Nettoyage local et archivage du paquet logiciel immuable
cd ~/API_Factory/Sentiment_Alpha_v1/
tar --exclude='venv' --exclude='__pycache__' --exclude='.git' -czf ../$ARCHIVE_NAME .

echo "[2/5] Teleporting secure package to VPS via SSH..."
# Transfert sécurisé de l'archive vers la forteresse Cloud
scp -i $SSH_KEY ../$ARCHIVE_NAME $VPS_USER@$VPS_IP:~/

echo "[3/5] Executing Remote Infrastructure Deployment..."
# Connexion SSH non interactive pour instancier le système
ssh -i $SSH_KEY $VPS_USER@$VPS_IP << EOF
    # Préparation du répertoire de production
    mkdir -p $REMOTE_DIR
    mv ~/$ARCHIVE_NAME $REMOTE_DIR/
    cd $REMOTE_DIR
    
    # Extraction atomique du paquet
    tar -xzf $ARCHIVE_NAME
    rm $ARCHIVE_NAME
    
    # Vérification de la présence du fichier de production .env
    if [ ! -f .env ]; then
        echo "[WARNING] .env missing on VPS! Cloning from example..."
        cp .env.example .env
        echo "Modify the remote .env with real production API keys."
    fi
    
    # Relance de la forteresse Docker (Sympathie Mécanique active)
    echo "[Remote] Rebuilding and launching Docker containers..."
    docker compose build --no-cache
    docker compose up -d
    
    echo "[Remote] Systemd / Docker check verification..."
    docker compose ps
EOF

# Nettoyage du package local
rm ../$ARCHIVE_NAME

echo "[4/5] Testing public endpoint gateway response..."
sleep 4
# Test immédiat du Paywall public distant
curl -s -I -X POST "http://$VPS_IP:8002/analyze/compare" | grep "Server"

echo "[5/5] DEPLOYMENT SUCCESSFUL. Meridian Alpha Systems is Global."
