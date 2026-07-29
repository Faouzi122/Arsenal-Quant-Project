# 📖 Arsenal Decision Engine - Developer Cookbook

> **Method**: the Breakeven Corridor is a deterministic algebraic boundary (where IL = accumulated yield), not a probabilistic model. The backtest script and its raw result files are published in [`07_Backtest_Engine/`](../07_Backtest_Engine/) — 180 days of real ETH/USDC daily closes. This engine measures; it does not forecast, and no predictive-accuracy figure is claimed.

This cookbook provides the exact integration blueprints to equip your autonomous agents (CrewAI, LangChain, ElizaOS) with our deterministic $\mathcal{O}(1)$ Risk Middleware.

## The Concept: L402 Deterministic Paywall
`evaluate_pool` gives you **100 free calls per IP per day, custom parameters included** — you can integrate and test without any Lightning wallet. Past that quota, your agent intercepts an HTTP 402, pays a Lightning invoice (currently **150 sats**, set by server configuration — always read the amount from the 402 response rather than hard-coding it), and retries with the cryptographic proof to unlock the decision matrix (`r_net_pct`, `risk_level`, `breakeven_corridor`).

Two endpoints expose the same calculation: `POST /mcp` (MCP JSON-RPC — `initialize` → `tools/list` → `tools/call`, the route advertised on the MCP registry) and `GET /mcp/evaluate` (REST convenience, GET-only). The example below uses the REST route.

## 🛠️ Python Integration (Universal / CrewAI Tool)

You can wrap this logic into a custom `@tool` for your CrewAI or LangChain agents.

```python
import urllib.request
import urllib.error
import json
import re

class ArsenalRiskShield:
    def __init__(self, lnbits_payment_key: str, lnbits_url: str = "https://demo.lnbits.com"):
        # LNbits needs a wallet key with send permission to pay an invoice. Use a
        # DEDICATED wallet funded with a small working balance — never the key of a
        # wallet holding significant funds. Load it from the environment, not code.
        self.lnbits_key = lnbits_payment_key
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
shield = ArsenalRiskShield(lnbits_payment_key=os.getenv("LNBITS_PAYMENT_KEY"))
evaluation = shield.request_risk_evaluation(apy=0.20, price_ratio=0.85, days_held=30)

print(f"Risk Level: {evaluation['risk_level']}") 
print(f"R_net: {evaluation['r_net_pct']:+.4f}%")
print(f"Breakeven Corridor: [{evaluation['breakeven_corridor']['lower_ratio']}, {evaluation['breakeven_corridor']['upper_ratio']}]")
```

## Why pay for evaluations?

This engine does not prevent losses and makes no claim about how much it saves you. It computes — deterministically, in O(1), with an HMAC signature over the result — whether a position sits above or below its breakeven boundary. What a paid call buys is a reproducible, auditable number your agent can act on. Start on the free quota; pay only if the calculation earns its place in your loop.
