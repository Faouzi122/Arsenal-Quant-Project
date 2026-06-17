#!/usr/bin/env python3
import sys
import os
import re
import json
import requests

# Set output color coding for professional log messages
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log_info(msg):
    print(f"{BLUE}[*] {msg}{RESET}")

def log_success(msg):
    print(f"{GREEN}[✓] {msg}{RESET}")

def log_warn(msg):
    print(f"{YELLOW}[!] {msg}{RESET}")

def log_error(msg):
    print(f"{RED}[✗] {msg}{RESET}")

def load_env_variables():
    # Attempt to load LNbits keys from the .env file in 06_Router_MCP
    env_path = os.path.join(os.path.dirname(__file__), "..", "06_Router_MCP", ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        env_vars[parts[0].strip()] = parts[1].strip()
    
    # Fallback to system env
    lnbits_url = env_vars.get("LNBITS_URL") or os.getenv("LNBITS_URL") or "https://demo.lnbits.com"
    
    # Check if an explicit admin key is provided in env, else fallback to invoice key
    lnbits_key = os.getenv("LNBITS_ADMIN_KEY") or env_vars.get("LNBITS_ADMIN_KEY")
    is_admin = True
    
    if not lnbits_key:
        lnbits_key = os.getenv("LNBITS_INVOICE_KEY") or env_vars.get("LNBITS_INVOICE_KEY")
        is_admin = False
    
    return lnbits_url, lnbits_key, is_admin

def main():
    print(f"{BOLD}================================================================{RESET}")
    print(f"{BOLD}       ANTIGRAVITY CLIENT ZERO : AUTOMATED L402 A2A AGENT       {RESET}")
    print(f"{BOLD}================================================================{RESET}")
    
    lnbits_url, lnbits_key, is_admin = load_env_variables()
    if not lnbits_key:
        log_error("LNbits Admin/Invoice Key not found in 06_Router_MCP/.env or environment.")
        sys.exit(1)
        
    if not is_admin:
        log_warn("Using Read-only Invoice Key. Payments will fail unless a valid Admin Key is set via LNBITS_ADMIN_KEY.")
    else:
        log_success("Admin Key detected. Authorized to execute out-of-wallet payments.")
        
    log_success(f"LNbits Wallet connection initialized: {lnbits_url}")
    
    # Phase 1: MCP Tool Discovery
    log_info("PHASE 1: Fetching MCP Server Card (Auto-Discovery)...")
    server_card_url = "https://api.arsenal-quant.com/.well-known/mcp/server-card.json"
    try:
        resp = requests.get(server_card_url, timeout=10)
        resp.raise_for_status()
        card = resp.json()
        server_info = card.get("serverInfo", {})
        log_success(f"Discovered Server: {server_info.get('name')} v{server_info.get('version')}")
        log_info(f"Description: {server_info.get('description')}")
        
        # Discover mev_security_audit tool
        tools = card.get("tools", [])
        mev_tool = next((t for t in tools if t.get("name") == "mev_security_audit"), None)
        if not mev_tool:
            log_error("Failed to discover 'mev_security_audit' tool in server card.")
            sys.exit(1)
        log_success(f"Discovered Tool: '{mev_tool['name']}' - Pricing: 150 SATs (L402)")
    except Exception as e:
        log_error(f"Failed to fetch server card: {e}")
        sys.exit(1)

    # Phase 2: Call MEV audit without credentials
    log_info("PHASE 2: Querying MEV Security Audit without L402 credentials...")
    target_url = "https://api.arsenal-quant.com/api/v1/arbitrage/mev"
    payload = {
        "victim_weth_in": 100.0,
        "attacker_weth_in": 10.0
    }
    
    try:
        resp = requests.post(target_url, json=payload, timeout=10)
    except Exception as e:
        log_error(f"Failed to connect to API endpoint: {e}")
        sys.exit(1)
        
    if resp.status_code != 402:
        log_error(f"Expected HTTP 402 Payment Required, got HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)
        
    log_success("HTTP 402 Payment Required received correctly.")
    
    # Phase 3: Parse L402 Challenge
    log_info("PHASE 3: Parsing WWW-Authenticate header...")
    auth_header = resp.headers.get("WWW-Authenticate")
    if not auth_header:
        log_error("WWW-Authenticate header missing in 402 response.")
        sys.exit(1)
        
    # Standard format: L402 macaroon="...", invoice="..."
    macaroon_match = re.search(r'macaroon="([^"]+)"', auth_header)
    invoice_match = re.search(r'invoice="([^"]+)"', auth_header)
    
    if not macaroon_match or not invoice_match:
        log_error("Failed to extract macaroon or invoice from WWW-Authenticate header.")
        sys.exit(1)
        
    macaroon = macaroon_match.group(1)
    invoice = invoice_match.group(1)
    
    log_success(f"Macaroon extracted: {macaroon[:20]}...")
    log_success(f"Lightning Invoice (Bolt11) extracted: {invoice[:30]}...")

    # Phase 4: Settle Invoice via LNbits
    log_info("PHASE 4: Settling Lightning Invoice via LNbits...")
    pay_url = f"{lnbits_url.rstrip('/')}/api/v1/payments"
    pay_headers = {
        "X-Api-Key": lnbits_key,
        "Content-Type": "application/json"
    }
    pay_payload = {
        "out": True,
        "bolt11": invoice
    }
    
    try:
        pay_resp = requests.post(pay_url, json=pay_payload, headers=pay_headers, timeout=15)
        pay_resp.raise_for_status()
        pay_data = pay_resp.json()
        preimage = pay_data.get("preimage")
        if not preimage:
            log_error(f"Preimage not returned by LNbits: {pay_data}")
            sys.exit(1)
        log_success(f"Invoice settled! Preimage: {preimage}")
    except Exception as e:
        log_error(f"Failed to pay Lightning invoice: {e}")
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
            print(f"\n{YELLOW}{BOLD}[DIAGNOSTIC - ACCÈS REFUSÉ (403)]{RESET}")
            print(f"La clé d'API fournie est une clé d'écriture de factures en lecture seule (Invoice Key).")
            print(f"Pour régler la facture, vous devez utiliser la clé d'administration (Admin Key) de votre wallet LNbits.")
            print(f"Exemple d'exécution :")
            print(f"  {BOLD}LNBITS_ADMIN_KEY=votre_cle_admin_ici python3 scripts/client_zero.py{RESET}\n")
        sys.exit(1)

    # Phase 5: Execute request with Authorization header
    log_info("PHASE 5: Retrying request with paid L402 token...")
    auth_header_value = f"L402 {macaroon}:{preimage}"
    headers = {
        "Authorization": auth_header_value,
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(target_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log_error(f"Failed during authorized execution: {e}")
        if 'resp' in locals():
            print(resp.text)
        sys.exit(1)
        
    log_success("HTTP 200 OK received!")
    
    # Phase 6: Display Decision Intelligence Output
    print(f"\n{BOLD}================================================================{RESET}")
    print(f"{BOLD}           DECISION INTELLIGENCE OUTPUT (MEV AUDIT)             {RESET}")
    print(f"{BOLD}================================================================{RESET}")
    decision = resp.json()
    print(json.dumps(decision, indent=2))
    print(f"{BOLD}================================================================{RESET}")
    
    signal = decision.get("signal")
    avoided_loss = decision.get("avoided_loss_usd", 0)
    
    if signal == "DELAY":
        log_success(f"PROVE OF ROI: Agent protected! Profit/Loss saved: ${avoided_loss:.2f} USD")
    else:
        log_info(f"Signal: {signal} - Clear execution window.")

if __name__ == "__main__":
    main()
