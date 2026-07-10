# Arsenal Decision Engine 🛡️
**The Risk-Validation Layer for Autonomous AI Agents (DeFAI)**

[![Arsenal-Quant-Project MCP server](https://glama.ai/mcp/servers/Faouzi122/Arsenal-Quant-Project/badges/card.svg)](https://glama.ai/mcp/servers/Faouzi122/Arsenal-Quant-Project)
[![smithery badge](https://smithery.ai/badge/khelifa-faouzi16/arsenal-decision-engine)](https://smithery.ai/servers/khelifa-faouzi16/arsenal-decision-engine)

> **Validation on 180-Day Binance ETH/USDC Data ([`07_Backtest_Engine/`](./decision_engine/07_Backtest_Engine/run_empirical_backtest.py)):**
> 🔬 **Breakeven Corridor** is a deterministic algebraic boundary (where IL = accumulated yield). Any position whose price ratio stays within `[lower_be, upper_be]` has R_net > 0 by mathematical definition — not a probabilistic model.
> 🎯 **82% to 97% Mid-Checkpoint Predictive Accuracy** — the risk level signal correctly predicted final position health (positive/negative R_net) across all tested APY × holding-period scenarios.

---

## Mission

**Transform DeFi uncertainty into deterministic, actionable risk metrics for autonomous agents.**
We do not run stateful trading bots or generate speculative prediction signals; we provide a stateless risk middleware layer that agents query before deploying or maintaining standard constant-product / full-range LP positions.

Built for agents, priced for agents. Pay per decision via Lightning Network (L402).

---

## What This Engine Does

Before an autonomous agent deploys capital or adjusts a standard constant-product / full-range LP position (such as Uniswap V2 or full-range V3), it submits the pool parameters (APY, price ratio, days held) to our API. The engine computes the exact mathematical risk, the net return ($R_{net}$), and the dynamic **Breakeven Corridor** bounds.

- **No LLMs. No hallucinations. Pure algebraic calculation.**
- **Complexity:** $\mathcal{O}(1)$ time and memory.
- **Latency:** $< 15\text{ms}$ local execution.

### Agent Request (HTTP GET)
```
https://api.arsenal-quant.com/mcp/evaluate?apy=0.20&price_ratio=0.85&days_held=30
```

### Engine Response (JSON Contract)
```json
{
  "impermanent_loss_pct": 0.3292,
  "accumulated_yield_pct": 1.6438,
  "r_net_pct": 1.3146,
  "il_to_yield_ratio": 0.2,
  "risk_level": "LOW",
  "breakeven_corridor": {
    "lower_ratio": 0.6941,
    "upper_ratio": 1.4407,
    "interpretation": "Position remains profitable if price ratio stays within [0.6941, 1.4407]"
  },
  "inputs": {
    "apy": 0.2,
    "price_ratio": 0.85,
    "days_held": 30
  },
  "source": "Arsenal Decision Engine v2.0",
  "oracle_signature": "b5dce8268fe762fa66ffccc083b02e9b65801888cdf76004ff22b648ea80869b",
  "layer": "PREMIUM"
}
```

---

## API Pricing (Dynamic L402)
- **Free Tier:** First 3 requests per IP/hour are free.
- **Low/Moderate Risk Positions:** 50 Sats per evaluation.
- **High/Critical Risk Positions:** 500 Sats per evaluation.

---

## Python Integration Example

```python
import urllib.request
import urllib.error
import json
import re
import os

API_URL = "https://api.arsenal-quant.com/mcp/evaluate?apy=0.20&price_ratio=0.85&days_held=30"
LNBITS_URL = "https://demo.lnbits.com"
LNBITS_ADMIN_KEY = os.getenv("LNBITS_ADMIN_KEY", "your_key_here")

def query_risk_oracle():
    req = urllib.request.Request(API_URL, method="GET")
    req.add_header("x-agent-id", "autonomous-lp-bot")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 402:
            auth_header = e.headers.get("WWW-Authenticate")
            macaroon = re.search(r'token="([^"]+)"', auth_header).group(1)
            invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)

            pay_req = urllib.request.Request(
                f"{LNBITS_URL}/api/v1/payments",
                data=json.dumps({"out": True, "bolt11": invoice}).encode(),
                headers={"X-Api-Key": LNBITS_ADMIN_KEY, "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(pay_req) as pay_resp:
                preimage = json.loads(pay_resp.read().decode())["preimage"]

            retry_req = urllib.request.Request(API_URL, method="GET")
            retry_req.add_header("Authorization", f"L402 {macaroon}:{preimage}")
            retry_req.add_header("x-agent-id", "autonomous-lp-bot")

            with urllib.request.urlopen(retry_req) as final_resp:
                return json.loads(final_resp.read().decode('utf-8'))
        else:
            raise

if __name__ == "__main__":
    evaluation = query_risk_oracle()
    print(f"Risk Level     : {evaluation['risk_level']}")
    print(f"R_net          : {evaluation['r_net_pct']:+.4f}%")
    print(f"Breakeven      : [{evaluation['breakeven_corridor']['lower_ratio']}, {evaluation['breakeven_corridor']['upper_ratio']}]")
```

---

## Developer Integration
- Integration cookbook & MCP guides: [`COOKBOOK.md`](./decision_engine/08_SDK_Wrappers/COOKBOOK.md)
- MCP auto-discovery card: `https://api.arsenal-quant.com/.well-known/mcp/server-card.json`

## Why L402? (Proof of Savings)
If this engine protects your agent from a $50,000 Impermanent Loss wipeout, a 500 Satoshi ($0.30) deterministic risk-validation call is not a cost — it is a mathematical insurance policy.
