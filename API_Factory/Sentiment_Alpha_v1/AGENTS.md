# AGENTS.md — Arsenal Decision Engine · Decision Intelligence Layer

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue?logo=modelcontextprotocol)](https://api.arsenal-quant.com/.well-known/mcp/server-card.json)
[![L402 Paywall](https://img.shields.io/badge/Payment-L402%20Lightning-orange)](https://github.com/lightning/bolts)
[![Latency](https://img.shields.io/badge/Latency-P99%20%3C%2015ms-green)]()
[![DeFAI](https://img.shields.io/badge/Domain-DeFAI%20%7C%20A2A-purple)]()

> **Mission**: Transform economic uncertainty into actionable decisions.
> Built for agents, priced for agents. Pay per decision in Satoshis.

---

## What This Engine Does

The Arsenal Decision Engine is a **consultative decision oracle** for autonomous DeFi agents.

You provide the market parameters. The engine returns a deterministic decision signal.
No hallucination. No LLM inference. Pure mathematical computation.

```
Agent input:   { mev_probability: 0.22, slippage: 0.004, gross_yield: 1500, ... }
Engine output: { signal: "DELAY", r_net: -23.4, confidence_score: 0.78, ... }
```

**Decision latency**: < 2ms p95 · **Network overhead**: < 15ms p99 via Cloudflare

---

## Use Cases for DeFi Agents

### 1. MEV / Sandwich Attack Risk Assessment

Before signing a transaction, submit your trade parameters to evaluate the
expected cost of a sandwich attack against your potential yield:

```python
import httpx, json

result = httpx.post(
    "https://api.arsenal-quant.com/analyze/arbitrage",
    headers={"X-API-Key": "YOUR_KEY"},
    json={
        "entry_price_usd":      2450.0,
        "exit_price_usd":       2510.0,
        "stop_loss_price_usd":  2420.0,
        "position_size_usd":    50000.0,
        "gross_yield_usd":      3000.0,
        "gas_usd":              12.0,
        "mev_probability":      0.22,       # Your bot's mempool estimate
        "slippage_pct":         0.004,
        "atr_values":           [18.0, 21.0, 25.0],
    }
).json()

if result["signal"] == "DELAY":
    print(f"Abort. MEV cost erodes yield: {result['cost_breakdown']['s_mev_usd']}$")
elif result["signal"] == "EXECUTE":
    print(f"Execute. R_net: {result['r_net_usd']}$ | Confidence: {result['confidence_score']}")
```

### 2. Impermanent Loss Guard (LP Positions)

```python
# Before adding liquidity to a pool:
result = httpx.post(
    "https://api.arsenal-quant.com/analyze/arbitrage",
    headers={"X-API-Key": "YOUR_KEY"},
    json={
        "entry_price_usd":      1.0,
        "exit_price_usd":       1.0,
        "stop_loss_price_usd":  0.9,
        "position_size_usd":    100000.0,
        "gross_yield_usd":      850.0,      # Expected LP fees
        "is_lp_position":       True,
        "il_price_ratio":       1.35,       # Price diverged 35%
    }
).json()

# signal=HEDGE → IL exceeds LP fees → withdraw liquidity
```

### 3. Funding Rate Contrarian Signal

```python
# Detect perpetual market overcrowding:
result = httpx.post(
    "https://api.arsenal-quant.com/analyze/arbitrage",
    headers={"X-API-Key": "YOUR_KEY"},
    json={
        "entry_price_usd":      43000.0,
        "exit_price_usd":       43500.0,
        "stop_loss_price_usd":  42000.0,
        "position_size_usd":    25000.0,
        "gross_yield_usd":      290.0,
        "funding_rate_8h":      0.00065,    # 0.065% — above 0.05% gate
        "holding_periods_8h":   3,
    }
).json()

# F5 filter fails → signal=DELAY → market is long-crowded
```

---

## MCP Integration (Pay-per-Decision via L402)

### Auto-Discovery

MCP-aware frameworks fetch the server card automatically:

```python
# Google ADK
from google.adk.tools import MCPToolset
toolset = MCPToolset.from_server_card(
    url="https://api.arsenal-quant.com/.well-known/mcp/server-card.json"
)

# ElizaOS — add to your agent config:
# mcp_servers: ["https://api.arsenal-quant.com/.well-known/mcp/server-card.json"]

# LangGraph / LangChain
from langchain_mcp import MCPClient
client = MCPClient("https://api.arsenal-quant.com/.well-known/mcp/server-card.json")
```

### Manual MCP Call (L402 Flow)

```python
import httpx

# Step 1: Call tool → receive 402 challenge
resp = httpx.post(
    "https://api.arsenal-quant.com/mcp/v1/tools/execute",
    json={
        "name": "evaluate_arbitrage_opportunity",
        "arguments": {
            "entry_price_usd":      2450.0,
            "exit_price_usd":       2510.0,
            "stop_loss_price_usd":  2420.0,
            "position_size_usd":    50000.0,
            "gross_yield_usd":      3000.0,
            "mev_probability":      0.22,
            "atr_values":           [18.0, 21.0, 25.0],
        }
    }
)

# Step 2: resp.status_code == 402
# resp.headers["WWW-Authenticate"] contains the Lightning invoice
# Also inspect resp.json()["decision_intelligence_fee"]["dynamic_amount"]
# to know the exact Satoshi amount for the current volatility tier.

# Step 3: Pay the invoice → get preimage
# Step 4: Retry with proof of payment
resp = httpx.post(
    "https://api.arsenal-quant.com/mcp/v1/tools/execute",
    headers={"Authorization": f"L402 {macaroon}:{preimage}"},
    json={"name": "evaluate_arbitrage_opportunity", "arguments": {...}}
)
decision = resp.json()["content"][0]["text"]
```

---

## Dynamic Uncertainty Pricing (DUP)

The L402 invoice amount scales with the **market volatility level** observed
by the engine (Prospect Theory — Kahneman & Tversky, 1979):

| Volatility | Invoice | Use case |
|-----------|---------|----------|
| `LOW`     | 150 sats (~$0.15) | Standard signal confirmation |
| `MEDIUM`  | 300 sats (~$0.30) | Confirmed trend, moderate risk |
| `HIGH`    | 1 500 sats (~$1.50) | Capital at risk |
| `EXTREME` | 5 000 sats (~$5.00) | Loss-avoidance signal |

The `decision_intelligence_fee.dynamic_amount` field in the 402 response
always shows the current tier — even in Shadow Mode (before strict enforcement).

---

## Available MCP Tools

| Tool name | Description | Latency p95 |
|-----------|-------------|-------------|
| `evaluate_arbitrage_opportunity` | R_net + 6 quant filters + IL/MEV/Funding | < 2ms |
| `analyze_market_psychology` | Fear/Greed Index from news text | < 2ms |
| `analyze_maritime_freight_risk` | Freight disruption risk per corridor | < 3ms |
| `compare_freight_corridors` | True Price: Transpacific vs Suez | < 5ms |

Full schema: [mcp-server.json](./mcp-server.json) · Live: [server-card.json](https://api.arsenal-quant.com/.well-known/mcp/server-card.json)

---

## Decision Output Schema (§4 Standard)

All tools return the same contract. **Read `signal` first**:

```json
{
  "signal":           "EXECUTE | HEDGE | DELAY | ALERT | MONITOR",
  "value":            <number>,
  "volatility":       "LOW | MEDIUM | HIGH | EXTREME",
  "trend":            "UP | DOWN | STABLE | ACCELERATING",
  "confidence_score": <0.0 - 0.99>,
  "context":          "<factual summary, max 120 chars>",
  "data_freshness_seconds": 0,
  "source":           "Arsenal Decision Engine v1.0"
}
```

**Confidence gating rule** (mandatory for autonomous execution):
```
confidence_score >= 0.85  → autonomous execution permitted
confidence_score <  0.60  → human review required
arbitration_required=true → human review mandatory (overrides score)
```

---

## Registries & Discovery

- **MCP Server Card**: `https://api.arsenal-quant.com/.well-known/mcp/server-card.json`
- **GitHub Topics**: `mcp-server` · `defai-agent` · `defi-arbitrage` · `a2a-protocol`
- **OpenAPI**: `https://api.arsenal-quant.com/docs`

---

*Arsenal Decision Engine — Decision Intelligence Layer v4.1.0*
*"If the agent saves $50,000 in MEV slippage, 150 sats is not the price — it is the insurance premium."*
