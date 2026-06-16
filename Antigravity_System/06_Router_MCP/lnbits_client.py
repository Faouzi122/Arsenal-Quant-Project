import urllib.request
import urllib.error
import json
import os

class LNbitsClient:
    """
    Lightweight REST API interface client for LNbits.
    Uses Python standard library urllib to minimize latency and memory bloat.
    """
    
    def __init__(self):
        # Retrieve configuration from environment or use default fallbacks
        self.base_url = os.getenv("LNBITS_URL", "http://localhost:5000").rstrip("/")
        self.api_key = os.getenv("LNBITS_INVOICE_KEY", "votre_cle_api_lnbits_ici")
        
    def create_invoice(self, amount_sats: int, memo: str) -> dict:
        """
        Generates a Lightning Network invoice on the LNbits node.
        """
        url = f"{self.base_url}/api/v1/payments"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = json.dumps({
            "out": False,
            "amount": amount_sats,
            "memo": memo
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                raw_data = response.read().decode("utf-8")
                return json.loads(raw_data)
        except Exception as e:
            print(f"[LNBITS CLIENT ERROR] Failed to create invoice: {e}")
            return {}

    def check_invoice(self, payment_hash: str) -> bool:
        """
        Queries LNbits to verify if the payment corresponding to the hash is settled.
        """
        url = f"{self.base_url}/api/v1/payments/{payment_hash}"
        headers = {
            "X-Api-Key": self.api_key
        }
        
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as response:
                raw_data = response.read().decode("utf-8")
                result = json.loads(raw_data)
                return result.get("paid", False)
        except Exception as e:
            print(f"[LNBITS CLIENT ERROR] Failed to check invoice: {e}")
            return False

