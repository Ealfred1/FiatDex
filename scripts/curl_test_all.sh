#!/bin/bash
# FiatDex API curl Test Suite
# Usage: bash scripts/curl_test_all.sh
# Requires: server running at localhost:8000

API="http://localhost:8000/api/v1"
PASS=0
FAIL=0

check() {
  local name="$1"
  local expected="$2"
  local actual="$3"
  if echo "$actual" | grep -qE "$expected"; then
    echo "✅ PASS: $name"
    ((PASS++))
  else
    echo "❌ FAIL: $name"
    echo "   Expected: $expected"
    echo "   Got: $(echo $actual | head -c 300)"
    ((FAIL++))
  fi
}

echo ""
echo "═══════════════════════════════════════════"
echo "  FiatDex API curl Test Suite"
echo "═══════════════════════════════════════════"
echo ""

# ── ROOT & HEALTH ─────────────────────────────────────────────────────────────
echo "--- Health ---"
R=$(curl -s "http://localhost:8000/health")
check "GET /health returns ok" "ok|status" "$R"

# ── AUTH ──────────────────────────────────────────────────────────────────────
echo ""
echo "--- Auth ---"

R=$(curl -s -X POST "$API/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"curltest@fiatdex.app","password":"CurlTest1","full_name":"Curl Tester","country":"NG"}')
check "POST /auth/signup returns 200 or 409" "message|email|already|detail" "$R"

R=$(curl -s -X POST "$API/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"weak@test.com","password":"weak","full_name":"Weak","country":"NG"}')
check "POST /auth/signup rejects weak password" "detail|422|password" "$R"

R=$(curl -s -X POST "$API/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"bad@test.com","password":"StrongPass1","full_name":"Bad","country":"XX"}')
check "POST /auth/signup rejects invalid country" "detail|422" "$R"

R=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"nobody@test.com","password":"WrongPass1"}')
check "POST /auth/login returns 401 for unknown user" "401|detail|credentials" "$R"

R=$(curl -s -X POST "$API/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email":"ghost@example.com"}')
check "POST /auth/forgot-password always 200" "message|email" "$R"

# ── WALLET AUTH ───────────────────────────────────────────────────────────────
echo ""
echo "--- Wallet Auth ---"

R=$(curl -s -X POST "$API/wallet/auth/nonce" \
  -H "Content-Type: application/json" \
  -d '{"wallet_address":"inj1testwalletaddress123456789012345678","wallet_type":"keplr"}')
check "POST /wallet/auth/nonce returns 200 with nonce" "nonce|message|200" "$R"

R=$(curl -s -X POST "$API/wallet/auth/nonce" \
  -H "Content-Type: application/json" \
  -d '{"wallet_address":"bad","wallet_type":"keplr"}')
check "POST /wallet/auth/nonce rejects bad address" "detail|422" "$R"

# ── TOKENS ────────────────────────────────────────────────────────────────────
echo ""
echo "--- Tokens ---"

R=$(curl -s "$API/tokens")
check "GET /tokens returns 200/503" "tokens|error|status|detail" "$R"

R=$(curl -s "$API/tokens?sort_by=gainers")
check "GET /tokens?sort_by=gainers accepted" "tokens|error|status|detail" "$R"

R=$(curl -s "$API/tokens?sort_by=invalid")
check "GET /tokens?sort_by=invalid returns 422" "422|detail|validation" "$R"

# ── AUTH REQUIRED (no token) ────────────────────────────────────────────────
echo ""
echo "--- Auth Required (no token) ---"

for endpoint in "portfolio" "portfolio/transactions" "funding/balance" "funding/history" "alerts" "alerts/watchlist" "wallet/balance"; do
  R=$(curl -s "$API/$endpoint")
  check "GET /$endpoint returns 401 without token" "401|Not authenticated|Authorization" "$R"
done

# ── ONRAMP ────────────────────────────────────────────────────────────────────
echo ""
echo "--- Onramp ---"

R=$(curl -s -X POST "$API/onramp/quote" \
  -H "Content-Type: application/json" \
  -d '{"fiat_amount":5000,"fiat_currency":"NGN","target_market_id":"0xaaaa","payment_method":"card"}')
check "POST /onramp/quote returns 401 without auth" "401|Not authenticated" "$R"

# ── WEBHOOK SECURITY ─────────────────────────────────────────────────────────
echo ""
echo "--- Webhook Security ---"

R=$(curl -s -X POST "$API/funding/webhook/paystack" \
  -H "Content-Type: application/json" \
  -d '{"event":"charge.success","data":{}}')
check "POST /funding/webhook/paystack rejects missing sig" "401|signature|Unauthorized" "$R"

R=$(curl -s -X POST "$API/onramp/webhook/transak" \
  -H "Content-Type: application/json" \
  -d '{"eventID":"ORDER_COMPLETED","data":{}}')
check "POST /onramp/webhook/transak rejects missing sig" "401|signature|Unauthorized" "$R"

# ── DOCS & OPENAPI ───────────────────────────────────────────────────────────
echo ""
echo "--- Documentation ---"

R=$(curl -s "http://localhost:8000/docs")
check "GET /docs returns 200" "200" "$R"

R=$(curl -s "http://localhost:8000/openapi.json")
check "GET /openapi.json returns valid JSON" "openapi|paths" "$R"
check "GET /openapi.json has /tokens path" "/tokens" "$R"
check "GET /openapi.json has /auth path" "/auth" "$R"
check "GET /openapi.json has /funding path" "/funding" "$R"

# ── SUMMARY ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  Results: ✅ $PASS passed  ❌ $FAIL failed"
echo "═══════════════════════════════════════════"
echo ""

if [ $FAIL -gt 0 ]; then
  exit 1
fi
