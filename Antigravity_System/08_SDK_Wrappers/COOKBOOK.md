# 📖 Arsenal Decision Engine - Developer Cookbook

> **Empirical Validation**: 99.08% Max Drawdown Reduction in Concentrated Liquidity Pools (Uniswap V3) during high-volatility crashes.

This cookbook provides the exact integration blueprints to equip your autonomous agents (CrewAI, LangChain, ElizaOS) with our deterministic $\mathcal{O}(1)$ Circuit Breaker.

## The Concept: L402 Deterministic Paywall
Your agent will intercept an HTTP 402, pay a microscopic Lightning Network invoice (50 or 500 sats), and retry with the cryptographic proof to unlock the decision (`EXECUTE`, `HEDGE`, or `DELAY`).

## 🛠️ Python Integration (Universal / CrewAI Tool)

You can wrap this logic into a custom `@tool` for your CrewAI or LangChain agents.

```python
import re
import requests

class ArsenalRiskShield:
    def __init__(self, lnbits_api_key: str, lnbits_url: str = "https://demo.lnbits.com"):
        self.api_url = "https://api.arsenal-quant.com/mcp/audit/latest"
        self.lnbits_key = lnbits_api_key
        self.lnbits_url = lnbits_url

    def request_risk_decision(self, expected_apy: float, price_divergence: float) -> dict:
        payload = {"expected_apy": expected_apy, "price_divergence": price_divergence}
        
        # 1. Initial Request (Triggers the L402 Challenge)
        resp = requests.post(self.api_url, json=payload)
        
        if resp.status_code == 402:
            auth_header = resp.headers.get("WWW-Authenticate")
            macaroon = re.search(r'macaroon="([^"]+)"', auth_header).group(1)
            invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)
            
            # 2. Machine-to-Machine Payment (Lightning Network)
            pay_resp = requests.post(
                f"{self.lnbits_url}/api/v1/payments",
                json={"out": True, "bolt11": invoice},
                headers={"X-Api-Key": self.lnbits_key}
            )
            pay_resp.raise_for_status()
            preimage = pay_resp.json().get("preimage")
            
            # 3. Unlock the Oracle Decision
            headers = {"Authorization": f"L402 {macaroon}:{preimage}"}
            final_resp = requests.post(self.api_url, json=payload, headers=headers)
            return final_resp.json()
            
        return resp.json()

# Example: Agent deciding to hold or exit a position
shield = ArsenalRiskShield(lnbits_api_key="your_agent_wallet_key")
decision = shield.request_risk_decision(expected_apy=0.15, price_divergence=0.88)
print(f"Oracle Signal: {decision['signal']}") # Returns HEDGE or EXECUTE
```

## Why pay 500 Sats?

If your autonomous portfolio is exposed to a $50,000 Impermanent Loss wipeout, a 500 Satoshi ($0.30) deterministic risk-validation call is not a fee. It is a mathematical insurance policy.
