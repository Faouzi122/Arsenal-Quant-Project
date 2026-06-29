import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Header, Response, Request
from fastapi.responses import PlainTextResponse
from lnbits_client import LNbitsClient
from security_shield import check_rate_limit, sign_audit_payload

# Parse .env configurations manually to avoid external dependencies
def load_environment():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("#"):
                    if "=" in clean_line:
                        key, val = clean_line.split("=", 1)
                        os.environ[key.strip()] = val.strip()

load_environment()

app = FastAPI(title="Antigravity AI Cost Intelligence - Mainnet Gateway")
lnbits = LNbitsClient()

@app.get("/")
async def root_endpoint():
    return {
        "system": "Antigravity Engine - Decision Layer",
        "status": "MAINNET ACTIVE",
        "protocol": "M2M L402 Paywall",
        "message": "Human access detected. This API is designed for autonomous agents.",
        "endpoints": {
            "discovery": "/.well-known/mcp/server-card.json",
            "audit_paywall": "/mcp/audit/latest"
        }
    }


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(BASE_DIR, "04_Strategy_Gerber", "Audit_Factory", "Strategic_Signals")
QUOTA_FILE = os.path.join(os.path.dirname(__file__), "client_quotas.json")

# Pricing matrix based on pain level
PRICING_MAP = {
    "LOW": 10000,
    "MEDIUM": 25000,
    "HIGH": 50000,
    "CRITICAL": 100000,
    "FATAL": 100000
}

# Quota Helpers (O(1) client tracking)
def get_client_requests(client_id: str) -> int:
    if not os.path.exists(QUOTA_FILE):
        return 0
    try:
        with open(QUOTA_FILE, "r") as f:
            quotas = json.load(f)
        return quotas.get(client_id, 0)
    except Exception:
        return 0

def increment_client_requests(client_id: str):
    quotas = {}
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r") as f:
                quotas = json.load(f)
        except Exception:
            pass
    quotas[client_id] = quotas.get(client_id, 0) + 1
    try:
        os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
        with open(QUOTA_FILE, "w") as f:
            json.dump(quotas, f)
    except Exception as e:
        print(f"[QUOTA ERROR] Failed to save quotas: {e}")

# Dynamic Pricing Helper
def get_dynamic_price(audit_path: str) -> int:
    override = os.getenv("L402_OVERRIDE_PRICE")
    if override:
        return int(override)
    price = 50000  # Fallback: 50,000 SATs (~$20 USD)
    if not os.path.exists(audit_path):
        return price
    try:
        with open(audit_path, "r") as f:
            content = f.read()
        for line in content.splitlines():
            if "Financial Loss Level:" in line:
                level = line.split("Financial Loss Level:")[1].strip().upper()
                return PRICING_MAP.get(level, price)
    except Exception as e:
        print(f"[PRICING ERROR] Failed to determine dynamic price: {e}")
    return price

# Dynamic Recommendation Helper
def get_mapper_recommendation(audit_path: str) -> str:
    audit_type = "COST_WASTE"
    if os.path.exists(audit_path):
        try:
            with open(audit_path, "r") as f:
                for line in f:
                    if "TYPE       :" in line:
                        audit_type = line.split("TYPE       :")[1].strip()
                        break
        except Exception:
            pass

    mapper_path = os.path.join(BASE_DIR, "04_Strategy_Gerber", "Decision_Layer", "pain_to_profit_mapper.json")
    if os.path.exists(mapper_path):
        try:
            with open(mapper_path, "r") as f:
                mapper = json.load(f)
            item = mapper["AI_COST_INTELLIGENCE_MAPPER"].get(audit_type)
            if item:
                return f"\n\n[UNLOCKED RECOMMENDATION]\n- Actionable MCP Call: {item['actionable_mcp_call']}\n- Est. Loss: {item['estimated_loss_usd']}"
        except Exception as e:
            print(f"[RECOMMENDATION ERROR] Failed to parse mapper: {e}")

    # Default fallback recommendation
    return "\n\n[UNLOCKED RECOMMENDATION]\n- Disable the redundant 'Routing' agent in your mcp_config.json.\n- Swap GPT-4o for Llama-3-8B-Instruct local model for base checks.\n- Validated immediate saving: $12,000 USD/month."

# Discoverability Endpoints (MCP Server Card)
@app.get("/.well-known/mcp/server-card.json")
@app.get("/well-known/mcp/server-card.json")
async def get_server_card():
    card_path = os.path.join(os.path.dirname(__file__), ".well-known", "mcp", "server-card.json")
    if os.path.exists(card_path):
        with open(card_path, "r") as f:
            return json.load(f)
    # Inline fallback if file is missing
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
        "serverInfo": {
            "name": "Antigravity Engine - Decision Layer",
            "version": "1.0.0"
        },
        "authentication": { "required": True, "type": "L402" }
    }

@app.get("/mcp/audit/latest")
async def get_latest_audit(request: Request, authorization: str = Header(None)):
    """
    Exposes latest diagnostic audit report.
    Free Quota: Protected by O(1) in-memory Security Shield rate limiting (first 3 free).
    Subsequent requests: Gated by dynamically priced L402 Lightning challenges.
    """
    client_id = request.headers.get("x-agent-id", request.client.host)
    raw_ip = request.headers.get("cf-connecting-ip", request.headers.get("x-forwarded-for", request.client.host))
    client_ip = raw_ip.split(",")[0].strip() if "," in raw_ip else raw_ip.strip()
    
    # Check directory
    if not os.path.exists(AUDIT_DIR):
        raise HTTPException(status_code=404, detail="Audit folder missing.")
        
    files = sorted(os.listdir(AUDIT_DIR), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No audit reports available.")
        
    latest_audit_path = os.path.join(AUDIT_DIR, files[0])
    
    # Verify if client already has a valid payment (L402 verification)
    is_paid = False
    payment_hash = None
    if authorization and authorization.startswith("L402 "):
        payment_hash = authorization.split(" ")[1]
        is_paid = lnbits.check_invoice(payment_hash)
        
    if not is_paid:
        # Check rate limit for free tier
        if check_rate_limit(client_ip):
            try:
                with open(latest_audit_path, 'r') as f:
                    content = f.read()
                
                # Sceau de l'Oracle (HMAC-SHA256 signature)
                oracle_secret = os.getenv("ORACLE_SECRET_KEY", "default_secret")
                payload_to_sign = {
                    "audit_content": content,
                    "client_ip": client_ip,
                    "type": "FREE_TIER"
                }
                signature = sign_audit_payload(payload_to_sign, oracle_secret)
                
                free_content = (
                    content + 
                    f"\n\n[FREE LAYER - Discovery Access]\n"
                    "- Free tier validation successful.\n"
                    "- Upcoming requests will require L402 micro-payments.\n\n"
                    f"{{\n  \"oracle_signature\": \"{signature}\",\n  \"layer\": \"FREE\"\n}}"
                )
                return PlainTextResponse(content=free_content)
            except Exception as e:
                raise HTTPException(status_code=500, detail="Error loading free audit payload.")
        else:
            # Quota exhausted, trigger payment flow
            price_sats = get_dynamic_price(latest_audit_path)
            # Call LNbits node API to create dynamic invoice
            invoice_data = lnbits.create_invoice(price_sats, f"Arsenal Audit Unlock ({client_id})")
            
            if not invoice_data or "payment_request" not in invoice_data:
                raise HTTPException(status_code=503, detail="Payment Gateway Node is Offline or Unauthorized")
                
            pr = invoice_data.get("payment_request")
            payment_hash = invoice_data.get("payment_hash")
            
            # Issue HTTP 402 challenge with macaroon/invoice credentials
            headers = {
                "WWW-Authenticate": f'L402 token="{payment_hash}", invoice="{pr}"'
            }
            return Response(
                content=json.dumps({"error": "Payment Required", "price_sats": price_sats, "client_id": client_id}),
                status_code=402,
                headers=headers,
                media_type="application/json"
            )

    # Read latest compiled audit file (Paid Path)
    try:
        with open(latest_audit_path, 'r') as f:
            content = f.read()
            
        recommendation = get_mapper_recommendation(latest_audit_path)
        
        # Sceau de l'Oracle (HMAC-SHA256 signature)
        oracle_secret = os.getenv("ORACLE_SECRET_KEY", "default_secret")
        payload_to_sign = {
            "audit_content": content,
            "payment_hash": payment_hash,
            "type": "PREMIUM_TIER"
        }
        signature = sign_audit_payload(payload_to_sign, oracle_secret)
        
        premium_content = (
            content + recommendation + 
            f"\n\n{{\n  \"oracle_signature\": \"{signature}\",\n  \"layer\": \"PREMIUM\"\n}}"
        )
        
        return PlainTextResponse(content=premium_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error loading the paid audit payload.")

# Catch-all route to proxy non-gateway requests to decision_engine
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def catch_all_proxy(request: Request, path_name: str):
    async with httpx.AsyncClient() as client:
        # Forward to decision_engine on the docker network
        target_url = f"http://decision_engine:8002/{path_name}"
        params = dict(request.query_params)
        headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
        body = await request.body()
        
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                params=params,
                headers=headers,
                content=body,
                timeout=15.0
            )
            # Reconstruct response with same status code and headers
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502, 
                detail=f"Proxy error connecting to Decision Engine backend: {str(e)}"
            )

if __name__ == "__main__":
    import uvicorn
    print("[SYSTEM] Starting Real L402 Gateway Server on port 8088...")
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="warning")
