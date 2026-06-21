import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Header, Response, Request
from fastapi.responses import PlainTextResponse
from lnbits_client import LNbitsClient

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

AUDIT_DIR = "/app/audit_data/"
QUOTA_FILE = os.path.join(os.path.dirname(__file__), "client_quotas.json")

PRICING_MAP = {
      "LOW": 10000,
      "MEDIUM": 25000,
      "HIGH": 50000,
      "CRITICAL": 100000,
      "FATAL": 100000
}

def get_client_requests(client_id):
      if not os.path.exists(QUOTA_FILE):
                return 0
            try:
                      with open(QUOTA_FILE, "r") as f:
                                    quotas = json.load(f)
                                return quotas.get(client_id, 0)
except Exception:
        return 0

def increment_client_requests(client_id):
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

def get_dynamic_price(audit_path):
    price = 50000
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
        print(f"[PRICING ERROR] {e}")
    return price

@app.get("/.well-known/mcp/server-card.json")
@app.get("/well-known/mcp/server-card.json")
      async def get_server_card():
            card_path = os.path.join(os.path.dirname(__file__), ".well-known", "mcp", "server-card.json")
    if os.path.exists(card_path):
              with open(card_path, "r") as f:
                            return json.load(f)
                    return {
                              "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
                              "serverInfo": {"name": "Antigravity Engine - Decision Layer", "version": "1.0.0"},
                              "authentication": {"required": True, "type": "L402"}
                    }
@app.get("/mcp/audit/latest")
async def get_latest_audit(request: Request, authorization: str = Header(None)):
      client_id = request.headers.get("x-agent-id", request.client.host)
    if not os.path.exists(AUDIT_DIR):
              raise HTTPException(status_code=404, detail="Audit folder missing.")
    files = sorted(os.listdir(AUDIT_DIR), reverse=True)
    if not files:
              raise HTTPException(status_code=404, detail="No audit reports available.")
    latest_audit_path = os.path.join(AUDIT_DIR, files[0])
    requests_count = get_client_requests(client_id)
    if requests_count < 3:
              increment_client_requests(client_id)
        try:
                      with open(latest_audit_path, "r") as f:
                                        content = f.read()
                                    free_content = content + f"\n\n[FREE LAYER - {requests_count + 1}/3]"
            return PlainTextResponse(content=free_content)
except Exception:
            raise HTTPException(status_code=500, detail="Error loading audit.")
    price_sats = get_dynamic_price(latest_audit_path)
    if not authorization or not authorization.startswith("L402 "):
              invoice_data = lnbits.create_invoice(price_sats, f"Audit ({client_id})")
        if not invoice_data or "payment_request" not in invoice_data:
                      raise HTTPException(status_code=503, detail="Payment Gateway Offline")
        pr = invoice_data.get("payment_request")
        payment_hash = invoice_data.get("payment_hash")
        headers = {"WWW-Authenticate": f'L402 token="{payment_hash}", invoice="{pr}"'}
        return Response(
                      content=json.dumps({"error": "Payment Required", "price_sats": price_sats}),
                      status_code=402, headers=headers, media_type="application/json"
        )
    payment_hash = authorization.split(" ")[1]
    is_paid = lnbits.check_invoice(payment_hash)
    if not is_paid:
              raise HTTPException(status_code=403, detail="Invoice unpaid.")
    try:
              with open(latest_audit_path, "r") as f:
                            content = f.read()
                        return PlainTextResponse(content=content)
except Exception:
                raise HTTPException(status_code=500, detail="Error loading paid audit.")

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def catch_all_proxy(request: Request, path_name: str):
      async with httpx.AsyncClient() as client:
                target_url = f"http://decision_engine:8002/{path_name}"
        params = dict(request.query_params)
        headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
        body = await request.body()
        try:
                      response = await client.request(
                          method=request.method, url=target_url, params=params,
                          headers=headers, content=body, timeout=15.0
        )
            return Response(
                              content=response.content, status_code=response.status_code,
                              headers=dict(response.headers), media_type=response.headers.get("content-type")
            )
except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

if __name__ == "__main__":
      import uvicorn
    print("[SYSTEM] Starting Real L402 Gateway Server on port 8088...")
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="warning")
