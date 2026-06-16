#!/bin/bash
# Client simulation demonstrating L402 request flow
# Complies with Antigravity Engine system engineering standards

echo "[CLIENT AGENT] Attempting to access decision intelligence..."
echo "---"

# Test 1: Query without credentials (expects HTTP 402 + invoice challenge header)
echo "> Test 1: Query without L402 header"
curl -i -s -X GET https://api.arsenal-quant.com/mcp/audit/latest | grep -E "HTTP|WWW-Authenticate"
echo "---"

# Test 2: Query with paid mockup macaroon (expects HTTP 200 + payload)
echo "> Test 2: Query with paid L402 token"
curl -s -X GET https://api.arsenal-quant.com/mcp/audit/latest \
     -H "Authorization: L402 AgEEbW...mock_macaroon_signature" | tail -n 8

echo "---"

