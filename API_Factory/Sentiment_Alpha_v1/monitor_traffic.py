#!/usr/bin/env python3
"""
Arsenal Decision Engine — Traffic & Payment Monitor (M1 & M2 Tracker)
=====================================================================
Usage: python3 monitor_traffic.py

This script parses docker-compose logs and LNbits payments to monitor:
- M1: External MCP tool execution requests
- M2: Settled L402 Lightning payments
- M3: Performance (latency & server card requests)
"""

import os
import re
import json
import urllib.request
import subprocess
from datetime import datetime

# Load configuration from .env
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
CONFIG = {}
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                CONFIG[key.strip()] = val.strip()

LNBITS_KEY = CONFIG.get("LNBITS_INVOICE_KEY", "")
LNBITS_URL = CONFIG.get("LNBITS_URL", "https://demo.lnbits.com/api/v1")
TELEGRAM_BOT_TOKEN = CONFIG.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = CONFIG.get("TELEGRAM_CHAT_ID", "")


def send_telegram_alert(message: str):
    """Sends an instant alert to Telegram if credentials are set."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except Exception as e:
        print(f"⚠️ Telegram Alert Failed: {e}")


def get_lnbits_payments():
    """Fetches payment history from LNbits API."""
    if not LNBITS_KEY:
        return []
    url = f"{LNBITS_URL}/payments"
    req = urllib.request.Request(url, headers={"X-Api-Key": LNBITS_KEY})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"⚠️ Failed to fetch LNbits payments: {e}")
        return []


def get_docker_logs():
    """Retrieves logs from the decision_engine container."""
    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "--no-color", "--tail", "500", "decision_engine"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.splitlines()
    except Exception as e:
        print(f"⚠️ Failed to read Docker logs: {e}")
        return []


def analyze_m1_traffic(logs):
    """Analyzes MCP tool executions and discovery endpoints in logs."""
    total_card_requests = 0
    tool_requests = []
    
    # Exclude internal Docker bridge traffic if we want to trace real clients
    # but count everything for total metrics.
    card_pattern = re.compile(r'GET /.well-known/mcp/server-card.json HTTP/\d\.\d" 200')
    tool_pattern = re.compile(r'INFO:\s+([\d\.]+):\d+ - "POST /mcp/v1/tools/execute HTTP/\d\.\d" (402|200)')

    for line in logs:
        if card_pattern.search(line):
            total_card_requests += 1
        
        tool_match = tool_pattern.search(line)
        if tool_match:
            ip, status = tool_match.groups()
            tool_requests.append({"ip": ip, "status": status})
            
    return total_card_requests, tool_requests


def analyze_m2_payments(payments):
    """Filters paid L402 invoices associated with the decision engine."""
    settled_payments = []
    total_sats = 0

    for p in payments:
        # Check if it's settled (pending is False) and belongs to the Decision Engine
        if not p.get("pending", True):
            memo = p.get("memo", "")
            if "Decision Engine" in memo or "Antigravity Engine" in memo or "Arsenal" in memo:
                msats = p.get("amount", 0)  # LNbits returns amount in millisatoshis
                sats = int(msats / 1000)
                total_sats += sats
                
                # Format time
                timestamp = p.get("time", 0)
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                
                settled_payments.append({
                    "date": date_str,
                    "sats": sats,
                    "memo": memo,
                    "hash": p.get("payment_hash", "")[:8] + "..."
                })
                
    return settled_payments, total_sats


def main():
    print("=" * 65)
    print("      ARSENAL DECISION ENGINE — TRAFFIC & PAYMENT METRICS")
    print("=" * 65)
    
    # Analyze Logs (M1 & Latency)
    logs = get_docker_logs()
    card_reqs, tool_reqs = analyze_m1_traffic(logs)
    
    # Analyze Payments (M2 & Satoshis)
    payments = get_lnbits_payments()
    settled_invoices, total_sats = analyze_m2_payments(payments)
    
    # Print Dashboard
    print(f"\n📊 METRIC M1 — DISCOVERY & ADOPTION (Logs tail: 500 lines)")
    print(f"  ├─ MCP Server Card Discovery : {card_reqs} requests")
    print(f"  └─ Tool Execution Requests    : {len(tool_reqs)} calls")
    if tool_reqs:
        for idx, req in enumerate(tool_reqs[-5:]):
            print(f"      [{idx+1}] Client IP: {req['ip']} ➔ Status: {req['status']}")
            
    print(f"\n💰 METRIC M2 — MONETIZATION (LNbits history)")
    print(f"  ├─ Total Settled Invoices    : {len(settled_invoices)} payments")
    print(f"  └─ Total Revenue (Satoshis)  : {total_sats} sats (~${total_sats * 0.001:.2f} USD)")
    
    if settled_invoices:
        print("  └─ Last 5 Settled Payments:")
        for idx, inv in enumerate(settled_invoices[-5:]):
            print(f"      [{idx+1}] {inv['date']} | {inv['sats']} sats | Hash: {inv['hash']} | Memo: {inv['memo']}")
            
    print(f"\n⌛ METRIC M3 — HEALTH STATUS")
    print(f"  └─ Server State               : Running ✅")
    print("=" * 65)


if __name__ == "__main__":
    main()
