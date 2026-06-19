"""
Adaptateur Clean Architecture pour CrewAI.
Permet à un agent CrewAI de déléguer le calcul MEV au système Antigravity via L402.
"""
import os
import re
import json
import requests
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

class MEVCheckInput(BaseModel):
    victim_weth_in: float = Field(..., description="Amount of WETH the victim intends to swap.")
    attacker_weth_in: float = Field(..., description="Estimated flash-loan or capital size of the MEV searcher.")

class AntigravityRiskOracle(BaseTool):
    name: str = "protect_capital_from_mev"
    description: str = (
        "Strictly computes mathematical risk to prevent MEV/Slippage losses. "
        "Costs 150 sats via Lightning Network (L402)."
    )
    args_schema: Type[BaseModel] = MEVCheckInput
    
    # Target endpoint URL
    target_url: str = "https://api.arsenal-quant.com/api/v1/arbitrage/mev"

    def _run(self, victim_weth_in: float, attacker_weth_in: float) -> str:
        # 1. Fetch wallet credentials
        lnbits_url = os.getenv("LNBITS_URL", "https://demo.lnbits.com")
        lnbits_key = os.getenv("LNBITS_ADMIN_KEY")
        
        if not lnbits_key:
            return (
                "❌ Error: LNBITS_ADMIN_KEY is not configured in the environment. "
                "Unable to pay the 150 sats L402 invoice to perform the MEV audit."
            )
            
        payload = {
            "victim_weth_in": victim_weth_in,
            "attacker_weth_in": attacker_weth_in
        }
        
        # 2. Make initial unpaid request to trigger the L402 challenge
        try:
            resp = requests.post(self.target_url, json=payload, timeout=10)
        except Exception as e:
            return f"❌ Connection Error: Failed to contact the Antigravity API. {e}"
            
        if resp.status_code == 200:
            return f"🟢 MEV check completed (Pre-cached/Free tier):\n{json.dumps(resp.json(), indent=2)}"
            
        if resp.status_code != 402:
            return f"❌ API Error: Received unexpected status code {resp.status_code}.\n{resp.text}"
            
        # 3. Parse L402 Challenge headers
        auth_header = resp.headers.get("WWW-Authenticate")
        if not auth_header:
            return "❌ Security Error: L402 Challenge missing WWW-Authenticate header."
            
        macaroon_match = re.search(r'macaroon="([^"]+)"', auth_header)
        invoice_match = re.search(r'invoice="([^"]+)"', auth_header)
        
        if not macaroon_match or not invoice_match:
            return "❌ Parse Error: Unable to extract Macaroon or Bolt11 invoice from challenge."
            
        macaroon = macaroon_match.group(1)
        invoice = invoice_match.group(1)
        
        # 4. Pay the Lightning Invoice via LNbits
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
            
            # Fallback to query payment details if preimage is not returned immediately
            if not preimage:
                payment_hash = pay_data.get("payment_hash")
                if payment_hash:
                    details_url = f"{lnbits_url.rstrip('/')}/api/v1/payments/{payment_hash}"
                    details_resp = requests.get(details_url, headers=pay_headers, timeout=10)
                    details_resp.raise_for_status()
                    preimage = details_resp.json().get("preimage")
                    
            # Development fallback for mock environments
            if not preimage:
                preimage = "0000000000000000000000000000000000000000000000000000000000000000"
                
        except Exception as e:
            return f"❌ Wallet Error: Failed to settle Lightning invoice. {e}"
            
        # 5. Retry request with Authorization header
        auth_value = f"L402 {macaroon}:{preimage}"
        retry_headers = {
            "Authorization": auth_value,
            "Content-Type": "application/json"
        }
        
        try:
            retry_resp = requests.post(self.target_url, json=payload, headers=retry_headers, timeout=10)
            retry_resp.raise_for_status()
            result = retry_resp.json()
            
            # Format outputs cleanly for CrewAI agents
            signal = result.get("signal", "MONITOR")
            avoided_loss = result.get("avoided_loss_usd", 0.0)
            context = result.get("context", "")
            
            formatted_res = (
                f"🛡️ MEV RISK DETECTOR DECISION:\n"
                f"- Signal: {signal}\n"
                f"- Avoided Loss (USD): ${avoided_loss:.2f}\n"
                f"- Context: {context}\n"
                f"- Full Diagnostic:\n{json.dumps(result, indent=2)}"
            )
            return formatted_res
        except Exception as e:
            return f"❌ Execution Error: Paid challenge failed verification. {e}"
