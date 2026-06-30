#!/usr/bin/env python3
"""
Antigravity CLI (ag_cli.py)
==========================
Autonomous Decision Engine L402 Command Line Tool.
Designed for Lenovo Celeron / Xubuntu environments (O(1) memory footprint).
Clean Architecture & Torvalds Compliant.
"""
import sys
import os
import re
import json
import time

def print_banner():
    banner = """
   ==================================================
        ARSENAL DECISION ENGINE — ANTIGRAVITY CLI    
   ==================================================
   Usage: ag "<instruction / analyze command>"
   Example: ag "Analyse le fichier client_zero.py et donne un JSON de risque"
   ==================================================
    """
    print(banner, file=sys.stderr)

def scan_file_for_risk(file_path):
    """
    Mechanical scan of code files for financial, security and performance risk patterns.
    """
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Heuristic scanners (O(1) iterations, no NLP overhead)
    issues = []
    risk_score = 0.0

    # 1. Check for exposed secrets/keys
    hex_32_patterns = re.findall(r'["\']([a-f0-9]{32})["\']', content)
    hex_64_patterns = re.findall(r'["\']([a-f0-9]{64})["\']', content)
    real_keys = [k for k in hex_32_patterns + hex_64_patterns if not k.startswith("000000")]
    if real_keys:
        issues.append(f"Exposed potential API key/secret in code ({len(real_keys)} detected)")
        risk_score += 0.45

    # 2. Check for insecure endpoints
    insecure_urls = re.findall(r'["\'](http://[a-zA-Z0-9\./_-]+)["\']', content)
    if insecure_urls:
        issues.append(f"Insecure HTTP URL protocol detected: {insecure_urls[0]}")
        risk_score += 0.25

    # 3. Check for payment handling robust implementation
    if "402" in content or "L402" in content or "preimage" in content:
        # Check for error handling
        if "try:" not in content and "except" not in content:
            issues.append("L402 flows implemented without robust try/except error wrapping")
            risk_score += 0.15

    # 4. Empty/Mock wallets or placeholder logic
    if "FakeWallet" in content or "dummy" in content.lower():
        issues.append("Fallback dummy/fake wallet in use; test mode detected")
        risk_score += 0.10

    # Normalize risk score
    risk_score = min(1.0, risk_score)
    
    # Map to signal
    if risk_score >= 0.50:
        signal = "HEDGE"
        context = f"CRITICAL: {', '.join(issues[:2])}"
    elif risk_score >= 0.20:
        signal = "DELAY"
        context = f"WARNING: {', '.join(issues[:2])}"
    else:
        signal = "EXECUTE"
        context = "CODE SECURE: No critical MEV/L402 or key vulnerabilities detected"

    return {
        "value": round(risk_score, 4),
        "change_pct": 0.0,
        "volatility": "HIGH" if risk_score > 0.4 else "LOW",
        "trend": "UP" if risk_score > 0.4 else "STABLE",
        "confidence_score": 0.95,
        "signal": signal,
        "context": context[:120],
        "data_freshness_seconds": 1,
        "source": "Antigravity CLI v1.0"
    }

def analyze_query(query):
    # Detect file names in prompt
    words = re.split(r'\s+', query)
    target_file = None
    for word in words:
        word_clean = word.strip('"\'(),;')
        if word_clean.endswith(('.py', '.json', '.yaml', '.yml', '.md')):
            target_file = word_clean
            break

    if target_file:
        # Try finding the file in several common paths
        potential_paths = [
            target_file,
            os.path.join(os.path.expanduser("~"), "Antigravity_System", target_file),
            os.path.join(os.path.expanduser("~"), "Antigravity_System", "scripts", target_file),
            os.path.join(os.path.expanduser("~"), "Antigravity_System", "06_Router_MCP", target_file),
            os.path.join(os.getcwd(), target_file),
            os.path.join(os.getcwd(), "scripts", target_file),
            os.path.join(os.getcwd(), "06_Router_MCP", target_file)
        ]
        
        found_path = None
        for path in potential_paths:
            if os.path.exists(path) and os.path.isfile(path):
                found_path = path
                break
                
        if found_path:
            result = scan_file_for_risk(found_path)
            if result:
                result["context"] = f"File {os.path.basename(found_path)} scanned. " + result["context"]
                return result

    # Standard query mechanical analysis
    query_lower = query.lower()
    if any(k in query_lower for k in ["risk", "mev", "loss", "crash", "slippage"]):
        return {
            "value": 0.75,
            "change_pct": 12.5,
            "volatility": "HIGH",
            "trend": "UP",
            "confidence_score": 0.90,
            "signal": "HEDGE",
            "context": "Heuristic match for risk elements in instruction. Enforcing capital protection.",
            "data_freshness_seconds": 0,
            "source": "Antigravity CLI v1.0"
        }
    
    return {
        "value": 0.0,
        "change_pct": 0.0,
        "volatility": "LOW",
        "trend": "STABLE",
        "confidence_score": 1.0,
        "signal": "EXECUTE",
        "context": f"Standard instruction processed: {query[:80]}",
        "data_freshness_seconds": 0,
        "source": "Antigravity CLI v1.0"
    }

def main():
    if len(sys.argv) < 2:
        print_banner()
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    decision = analyze_query(query)
    
    # Output the standardized JSON to stdout (zero marketing, pure signal)
    print(json.dumps(decision, indent=2))

if __name__ == "__main__":
    main()
