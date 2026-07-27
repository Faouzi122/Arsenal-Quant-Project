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
# Format: { (scope, "IP_ADDRESS"): [timestamp1, timestamp2, ...] }
# Clé composite (scope, ip) : les compteurs de chaque scope sont totalement
# isolés — consommer le quota "evaluate" ne touche jamais le quota "audit".
_RATE_LIMIT_STORE = defaultdict(list)

# Configuration Lean — un seuil nommé et sa fenêtre par scope d'usage.
# evaluate_pool : quota d'exploration ouvert pour mesurer l'usage réel.
EVALUATE_FREE_CALLS_PER_DAY = 100
EVALUATE_WINDOW_SECONDS = 86400  # 24 heures

# Route REST /mcp/audit/latest : paywall strict inchangé.
AUDIT_FREE_CALLS_PER_HOUR = 3
AUDIT_WINDOW_SECONDS = 3600  # 1 heure

# scope -> (nombre d'appels gratuits, fenêtre en secondes)
_SCOPE_LIMITS = {
    "evaluate": (EVALUATE_FREE_CALLS_PER_DAY, EVALUATE_WINDOW_SECONDS),
    "audit": (AUDIT_FREE_CALLS_PER_HOUR, AUDIT_WINDOW_SECONDS),
}

def check_rate_limit(client_ip: str, scope: str) -> bool:
    """
    Vérifie si (scope, IP) a dépassé son quota gratuit dans la fenêtre de
    temps propre à ce scope. Retourne True si autorisé, False si bloqué
    (Exige L402).

    `scope` est obligatoire et doit être une clé connue de _SCOPE_LIMITS
    ("evaluate" ou "audit"). Un scope inconnu lève un ValueError explicite
    plutôt que de retomber silencieusement sur un quota permissif.
    """
    if scope not in _SCOPE_LIMITS:
        raise ValueError(
            f"Unknown rate-limit scope: {scope!r}. Expected one of {sorted(_SCOPE_LIMITS)}."
        )

    max_free_calls, window_seconds = _SCOPE_LIMITS[scope]
    current_time = time.time()
    store_key = (scope, client_ip)

    # Nettoyage O(N) où N <= max_free_calls (donc O(1) effectif)
    _RATE_LIMIT_STORE[store_key] = [
        t for t in _RATE_LIMIT_STORE[store_key]
        if current_time - t < window_seconds
    ]

    if len(_RATE_LIMIT_STORE[store_key]) >= max_free_calls:
        return False # Quota épuisé, déclenchement du paywall L402

    # Ajout du nouvel appel
    _RATE_LIMIT_STORE[store_key].append(current_time)
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
