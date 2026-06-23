import httpx

class LNbitsClient:
          def __init__(self, api_url: str, admin_key: str, invoice_key: str = None):
                        self.api_url = api_url.rstrip('/')
                        self.admin_key = admin_key
                        self.invoice_key = invoice_key or admin_key

          async def create_invoice(self, amount_sats: int, memo: str) -> dict:
                        url = f"{self.api_url}/api/v1/payments"
                        headers = {
                            "X-Api-Key": self.admin_key,
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "out": False,
                            "amount": amount_sats,
                            "memo": memo
                        }
                        async with httpx.AsyncClient() as client:
                                          try:
                                                                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                                                                if response.status_code in (200, 201):
                                                                                          return response.json()
                                                                                                          return {}
            except Exception:
                    return {}

    async def check_invoice(self, payment_hash: str) -> bool:
                  url = f"{self.api_url}/api/v1/payments/{payment_hash}"
                  headers = {
                      "X-Api-Key": self.invoice_key
                  }
                  async with httpx.AsyncClient() as client:
                                    try:
                                                          response = await client.get(url, headers=headers, timeout=10.0)
                                                          if response.status_code == 200:
                                                                                    data = response.json()
                                                                                    return data.get("paid", False)
                                                                                return False
            except Exception:
                    return False
