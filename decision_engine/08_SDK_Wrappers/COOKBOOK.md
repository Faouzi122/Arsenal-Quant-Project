# 📖 Arsenal Decision Engine - Developer Cookbook

> **Empirical Validation**: 100% Breakeven Corridor Reliability. Positions that stayed within the calculated corridor completed their lifecycle with a positive net yield ($R_{net} > 0$) based on 180-day real ETH/USDC data.

This cookbook provides the exact integration blueprints to equip your autonomous agents (CrewAI, LangChain, ElizaOS) with our deterministic $\mathcal{O}(1)$ Risk Middleware.

## The Concept: L402 Deterministic Paywall
Your agent will intercept an HTTP 402, pay a microscopic Lightning Network invoice (50 or 500 sats), and retry with the cryptographic proof to unlock the decision matrix (`r_net_pct`, `risk_level`, and `breakeven_corridor`).

## 🛠️ Python Integration (Universal / CrewAI Tool)

You can wrap this logic into a custom `@tool` for your CrewAI or LangChain agents.

```python
import urllib.request
import urllib.error
import json
import re

class ArsenalRiskShield:
    def __init__(self, lnbits_api_key: str, lnbits_url: str = "https://demo.lnbits.com"):
        self.lnbits_key = lnbits_api_key
        self.lnbits_url = lnbits_url

    def request_risk_evaluation(self, apy: float, price_ratio: float, days_held: int = 30) -> dict:
        # 1. Build request target targeting the evaluate endpoint
        url = f"https://api.arsenal-quant.com/mcp/evaluate?apy={apy}&price_ratio={price_ratio}&days_held={days_held}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("x-agent-id", "autonomous-lp-bot")
        
        try:
            # First request (will work if under free tier)
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 402:
                # 2. Parse L402 HTTP challenge
                auth_header = e.headers.get("WWW-Authenticate")
                macaroon = re.search(r'token="([^"]+)"', auth_header).group(1)
                invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)
                
                # 3. Pay BOLT11 Invoice via LNbits API
                pay_req = urllib.request.Request(
                    f"{self.lnbits_url}/api/v1/payments",
                    data=json.dumps({"out": True, "bolt11": invoice}).encode(),
                    headers={"X-Api-Key": self.lnbits_key, "Content-Type": "application/json"}
                )
                with urllib.request.urlopen(pay_req) as pay_resp:
                    preimage = json.loads(pay_resp.read().decode())["preimage"]
                
                # 4. Retry with paid L402 token proof
                retry_req = urllib.request.Request(url, method="GET")
                retry_req.add_header("Authorization", f"L402 {macaroon}:{preimage}")
                retry_req.add_header("x-agent-id", "autonomous-lp-bot")
                
                with urllib.request.urlopen(retry_req) as final_resp:
                    return json.loads(final_resp.read().decode('utf-8'))
            else:
                raise

# Example: Agent deciding to hold or exit a position
shield = ArsenalRiskShield(lnbits_api_key="your_agent_wallet_key")
evaluation = shield.request_risk_evaluation(apy=0.20, price_ratio=0.85, days_held=30)

print(f"Risk Level: {evaluation['risk_level']}") 
print(f"R_net: {evaluation['r_net_pct']:+.4f}%")
print(f"Breakeven Corridor: [{evaluation['breakeven_corridor']['lower_ratio']}, {evaluation['breakeven_corridor']['upper_ratio']}]")
```

## Why pay for evaluations?

If your autonomous portfolio is exposed to a $50,000 Impermanent Loss wipeout, a 500 Satoshi ($0.30) deterministic risk-validation call is not a fee. It is a mathematical insurance policy protecting your LP margins.
