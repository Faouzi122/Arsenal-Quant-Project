# Arsenal Decision Engine 🛡️
**The Risk-Validation Layer for Autonomous AI Agents (DeFAI)**

[![Arsenal-Quant-Project MCP server](https://glama.ai/mcp/servers/Faouzi122/Arsenal-Quant-Project/badges/card.svg)](https://glama.ai/mcp/servers/Faouzi122/Arsenal-Quant-Project)
[![smithery badge](https://smithery.ai/badge/khelifa-faouzi16/arsenal-decision-engine)](https://smithery.ai/servers/khelifa-faouzi16/arsenal-decision-engine)

> **Method and raw results are published** — [backtest script](./decision_engine/07_Backtest_Engine/run_empirical_backtest.py) · [result data](./decision_engine/07_Backtest_Engine/data/) (180 days of Binance ETH/USDC daily closes):
> 🔬 **Breakeven Corridor** is a deterministic algebraic boundary (where IL = accumulated yield). Any position whose price ratio stays within `[lower_be, upper_be]` has R_net > 0 by mathematical definition — not a probabilistic model.
> 📐 This engine **measures**; it does not forecast. No predictive-accuracy figure is claimed — read the published result files and judge the method for yourself.

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

### Two ways to call it

**1. MCP JSON-RPC — the endpoint advertised on the MCP registry**
```
POST https://api.arsenal-quant.com/mcp
```
```json
{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{"name":"evaluate_pool",
           "arguments":{"apy":0.20,"price_ratio":0.85,"days_held":30}}}
```
Standard MCP handshake: `initialize` → `tools/list` → `tools/call`. Available over
streamable HTTP and stdio.

**2. REST convenience route — no MCP client required**
```
GET https://api.arsenal-quant.com/mcp/evaluate?apy=0.20&price_ratio=0.85&days_held=30
```
Both routes run the same calculation and the same quota. Note that
`/mcp/evaluate` is **GET-only**: a `POST` to that path returns `405 Allow: GET`,
because JSON-RPC belongs on `/mcp`.

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
  "oracle_signature": "<HMAC-SHA256 hex — illustrative placeholder, yours will differ>",
  "layer": "FREE"
}
```
`layer` reports how the call was served: `FREE` while inside the free quota,
`PREMIUM` once an L402 payment has been verified. The call shown above is
served as `FREE`.

---

## Access and Pricing

- **Free tier — `evaluate_pool`:** **100 calls per IP per day, custom parameters
  included.** No Lightning wallet is needed to use the engine.
- **Beyond the free quota:** an L402 Lightning micro-payment. The amount is set by
  server configuration and is currently **150 sats** per evaluation. Read it from
  the `WWW-Authenticate` header or from `error.data.price_sats` in the 402 response
  rather than hard-coding it.
- **`get_latest_audit`:** 3 free calls per IP per hour, then L402 — this endpoint
  is what keeps the Lightning rail live and demonstrable.

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

# LNbits requires a wallet key with send permission to pay an invoice.
# Use a DEDICATED wallet funded with a small working balance, and never the key
# of a wallet holding significant funds. Keep it in the environment, never in code.
LNBITS_PAYMENT_KEY = os.getenv("LNBITS_PAYMENT_KEY")

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
                headers={"X-Api-Key": LNBITS_PAYMENT_KEY, "Content-Type": "application/json"}
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

## Why pay per call?

This engine does not prevent losses, and it makes no claim about how much money it
saves you. What it does is compute — deterministically, in $\mathcal{O}(1)$, with an
HMAC signature over the result — whether a position sits above or below its
breakeven boundary. What you pay for is a reproducible, auditable number your agent
can act on, priced per call so it can be budgeted like any other input.
