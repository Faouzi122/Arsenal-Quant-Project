"""
MODULE : SECURITY SHIELD (Security & Rate Limiting)
COMPLEXITÉ : O(1) en mémoire RAM (Zéro I/O disque)
"""
import time
import hmac
import hashlib
import json
from collections import defaultdict

# Stockage en RAM pour des performances maximales (< 1ms)
# Format: { "IP_ADDRESS": [timestamp1, timestamp2, ...] }
_RATE_LIMIT_STORE = defaultdict(list)

# Configuration Lean
MAX_FREE_CALLS = 3
TIME_WINDOW_SECONDS = 3600  # 1 heure

def check_rate_limit(client_ip: str) -> bool:
    """
    Vérifie si l'IP a dépassé son quota gratuit dans la fenêtre de temps.
    Retourne True si autorisé, False si bloqué (Exige L402).
    """
    current_time = time.time()
    
    # Nettoyage O(N) où N <= 3 (donc O(1) effectif)
    _RATE_LIMIT_STORE[client_ip] = [
        t for t in _RATE_LIMIT_STORE[client_ip] 
        if current_time - t < TIME_WINDOW_SECONDS
    ]
    
    if len(_RATE_LIMIT_STORE[client_ip]) >= MAX_FREE_CALLS:
        return False # Quota épuisé, déclenchement du paywall L402
        
    # Ajout du nouvel appel
    _RATE_LIMIT_STORE[client_ip].append(current_time)
    return True

def sign_audit_payload(audit_data: dict, secret_key: str) -> str:
    """
    Génère une signature cryptographique HMAC-SHA256 (Le Sceau de l'Oracle).
    Garantit aux agents HFT que le signal n'a pas été altéré.
    """
    # Tri des clés pour garantir un hash déterministe
    payload_str = json.dumps(audit_data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature
