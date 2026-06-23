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
        self.base_url = os.getenv("LNBITS_URL", "http://localhost:5000").rstrip("/")
        self.api_key = os.getenv("LNBITS_INVOICE_KEY", "demo_key")

    def create_invoice(self, amount_sats, memo):
        url = f"{self.base_url}/api/v1/payments"
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        payload = json.dumps({"out": False, "amount": amount_sats, "memo": memo}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"[LNBITS ERROR] create_invoice: {e}")
            return {}

    def check_invoice(self, payment_hash):
        url = f"{self.base_url}/api/v1/payments/{payment_hash}"
        headers = {"X-Api-Key": self.api_key}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("paid", False)
        except Exception as e:
            print(f"[LNBITS ERROR] check_invoice: {e}")
            return False
