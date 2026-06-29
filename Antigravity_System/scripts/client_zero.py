#!/usr/bin/env python3
"""
CLIENT ZÉRO : Testeur de Paywall L402 M2M
============================================
Arsenal Decision Engine — Épreuve du Feu

Action : Tente d'accéder à l'Arsenal Decision Engine, intercepte l'erreur 402,
paie la facture Lightning, et récupère la décision.

Prérequis :
- Un wallet LNbits approvisionné (au moins 150 sats)
- Remplacer CLIENT_API_KEY par votre clé Admin LNbits

Usage : python3 client_zero.py
"""
import urllib.request
import urllib.error
import json
import re
import sys
import time

# ==============================================================================
# CONFIGURATION DU CLIENT (Ce portefeuille va PAYER les 150 sats)
# Remplacez par la clé Admin d'un wallet LNbits approvisionné
# ==============================================================================
CLIENT_WALLET_URL = "https://demo.lnbits.com"
CLIENT_API_KEY = "6174e2b5057a4e16a0609e6ef87b33ed"

# L'URL de votre serveur Arsenal Decision Engine
TARGET_API = "https://api.arsenal-quant.com/mcp/audit/latest"

# ==============================================================================
# FONCTIONS
# ==============================================================================

def print_banner():
    print()
    print("=" * 60)
    print("  CLIENT ZÉRO — Arsenal Decision Engine L402 Tester")
    print("  Mode : M2M (Machine-to-Machine) — Zéro Dépendance")
    print("=" * 60)
    print()

def pay_invoice(bolt11):
    """Paie une facture Lightning via le wallet LNbits du client."""
    print(f"  [💰] Initiation du paiement Lightning...")
    url = f"{CLIENT_WALLET_URL}/api/v1/payments"
    data = json.dumps({"out": True, "bolt11": bolt11}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "X-Api-Key": CLIENT_API_KEY,
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            payment_hash = result.get("payment_hash", "unknown")
            print(f"  [✅] Paiement réussi ! Hash: {payment_hash[:16]}...")
            return payment_hash
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")[:200]
        print(f"  [❌] Échec du paiement : HTTP {e.code} — {error_body}")
        return None
    except Exception as e:
        print(f"  [❌] Erreur réseau : {e}")
        return None

def run_mission():
    """Exécute la mission Client Zéro : accès → rejet → paiement → accès."""
    print_banner()

    if CLIENT_API_KEY == "REMPLACEZ_PAR_VOTRE_CLE_ADMIN_LNBITS_ICI":
        print("  [⚠️ ] ATTENTION : Vous devez configurer votre clé API LNbits.")
        print("  [⚠️ ] Ouvrez ce fichier et remplacez CLIENT_API_KEY ligne 32.")
        print("  [⚠️ ] Clé Admin depuis : https://demo.lnbits.com")
        print()
        # Mode simulation : on teste quand même la première requête
        print("  [ℹ️ ] Lancement en mode SIMULATION (sans paiement)...")
        print()

    # ──────────────────────────────────────────────────────────
    # PHASE 1 : Tentative d'accès (doit retourner 402)
    # ──────────────────────────────────────────────────────────
    print(f"  [1/3] 🔒 Tentative d'accès au serveur...")
    print(f"        URL : {TARGET_API}")
    print()

    req = urllib.request.Request(TARGET_API, headers={
        "User-Agent": "Client-Zero-Agent/1.0",
        "x-agent-id": "client-zero-test"
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            # Si on arrive ici, le serveur a donné l'accès (couche gratuite)
            content = response.read().decode("utf-8")
            print("  [🎁] Le serveur a accordé l'accès GRATUIT (Free Layer).")
            print()
            print("  " + "─" * 56)
            print("  RÉPONSE DE L'ORACLE (Free Tier) :")
            print("  " + "─" * 56)
            for line in content.split("\n")[:20]:
                print(f"  │ {line}")
            print("  " + "─" * 56)
            print()
            print("  [ℹ️ ] Vous avez 3 requêtes gratuites. Après ça, L402 s'active.")
            return True

    except urllib.error.HTTPError as e:
        if e.code == 402:
            # ──────────────────────────────────────────────────
            # PHASE 2 : Le mur L402 a bloqué — extraire la facture
            # ──────────────────────────────────────────────────
            print("  [✅] INFRASTRUCTURE VALIDÉE : Le serveur exige un paiement (402).")
            print()

            auth_header = e.headers.get("WWW-Authenticate", "")
            body = e.read().decode("utf-8")

            # Parse le body pour le prix
            try:
                body_json = json.loads(body)
                price = body_json.get("price_sats", "?")
                print(f"  [💵] Prix demandé : {price} sats")
            except Exception:
                pass

            # Extraction du token et de la facture via regex
            token_match = re.search(r'token="([^"]+)"', auth_header)
            invoice_match = re.search(r'invoice="([^"]+)"', auth_header)

            if not token_match or not invoice_match:
                print("  [❌] En-tête L402 malformé. Header reçu :")
                print(f"       {auth_header[:200]}")
                return False

            token = token_match.group(1)
            invoice = invoice_match.group(1)

            print(f"  [🔑] Token L402 : {token[:16]}...")
            print(f"  [⚡] Facture Lightning : {invoice[:40]}...")
            print()

            if CLIENT_API_KEY == "REMPLACEZ_PAR_VOTRE_CLE_ADMIN_LNBITS_ICI":
                print("  [⚠️ ] Mode SIMULATION : paiement non effectué.")
                print("  [ℹ️ ] Configurez CLIENT_API_KEY pour tester le paiement réel.")
                print()
                print("  " + "=" * 56)
                print("  RÉSULTAT : PHASE 1 VALIDÉE ✅")
                print("  Le paywall L402 fonctionne. Le serveur bloque correctement.")
                print("  " + "=" * 56)
                return True

            # ──────────────────────────────────────────────────
            # PHASE 3 : Paiement Lightning
            # ──────────────────────────────────────────────────
            print(f"  [2/3] ⚡ Paiement de la facture Lightning...")
            payment_hash = pay_invoice(invoice)

            if not payment_hash:
                print("  [❌] Le paiement a échoué. Vérifiez le solde du wallet.")
                return False

            print()
            time.sleep(1)  # Laisser le réseau propager

            # ──────────────────────────────────────────────────
            # PHASE 4 : Soumission de la preuve cryptographique
            # ──────────────────────────────────────────────────
            print(f"  [3/3] 🔓 Soumission de la preuve de paiement...")

            req_paid = urllib.request.Request(TARGET_API, headers={
                "User-Agent": "Client-Zero-Agent/1.0",
                "x-agent-id": "client-zero-test",
                "Authorization": f"L402 {token}"
            })

            try:
                with urllib.request.urlopen(req_paid, timeout=15) as final_resp:
                    audit_data = final_resp.read().decode("utf-8")
                    print()
                    print("  " + "=" * 56)
                    print("  ✅ ACCÈS DÉVERROUILLÉ — RÉPONSE DE L'ORACLE :")
                    print("  " + "=" * 56)
                    for line in audit_data.split("\n"):
                        print(f"  │ {line}")
                    print("  " + "=" * 56)
                    print()
                    print("  [🏆] BOUCLE MONÉTISATION M2M : VALIDÉE")
                    print("  [💰] Transaction : Agent → Lightning → Arsenal → Décision")
                    return True

            except urllib.error.HTTPError as err:
                print(f"  [❌] Preuve rejetée. Erreur {err.code}")
                try:
                    err_body = err.read().decode("utf-8")
                    print(f"       {err_body[:200]}")
                except Exception:
                    pass
                return False

        elif e.code == 404:
            print(f"  [⚠️ ] Serveur répond 404. L'endpoint n'existe pas encore.")
            print(f"       Vérifiez que le conteneur Docker tourne sur le VPS.")
            return False
        else:
            print(f"  [❌] Erreur inattendue : HTTP {e.code}")
            try:
                print(f"       {e.read().decode('utf-8')[:200]}")
            except Exception:
                pass
            return False

    except Exception as e:
        print(f"  [❌] Erreur de connexion : {e}")
        print(f"       Le VPS est-il allumé ? Le tunnel Cloudflare est-il actif ?")
        return False


if __name__ == "__main__":
    success = run_mission()
    print()
    sys.exit(0 if success else 1)
